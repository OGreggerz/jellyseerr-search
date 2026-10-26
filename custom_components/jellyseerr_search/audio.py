"""Anime audio: English dub or Japanese with subtitles, chosen per show (Sonarr)
or film (Radarr) by moving it between three quality profiles; and what the
downloaded files actually have, from the media info Sonarr and Radarr read.

The profiles are found by name. They're kept by Recyclarr on the home lab
(recyclarr.yml): a release named DUAL / DUBBED / a dub group, or tagged
English by the indexer, scores 2000 in the two dub profiles. A server
without them has no audio choice, and the card shows none."""

from __future__ import annotations

from typing import Any

AUDIO_DUB = "dub"  # dub preferred: Japanese with subtitles now, the dub replaces it
AUDIO_DUB_ONLY = "dub_only"  # nothing until a dub is posted
AUDIO_SUB = "sub"  # Japanese with subtitles; dubs avoided
AUDIO_CHOICES = (AUDIO_DUB, AUDIO_DUB_ONLY, AUDIO_SUB)
DUB_CHOICES = (AUDIO_DUB, AUDIO_DUB_ONLY)

PROFILE_NAMES = {
    AUDIO_DUB: "Anime (English dub preferred)",
    AUDIO_DUB_ONLY: "Anime (English dub only)",
    AUDIO_SUB: "Anime (Japanese + subtitles)",
}

# Custom formats that mean a release has English audio (TRaSH's two, and the
# home lab's local one for English-tagged MULTi releases).
DUB_FORMATS = frozenset({"Dubs Only", "Anime Dual Audio", "Anime English (tagged)"})

# TMDB's "anime" keyword: what Seerr checks to send a show to its anime profile
# (MediaRequestSubscriber, ANIME_KEYWORD_ID). It misses some (Slime), so a
# Japanese animation counts too.
ANIME_KEYWORD_ID = 210024
ANIMATION_GENRE_ID = 16

# What a file's audio is, in the card's terms.
FILE_DUAL = "dual"  # English and another language
FILE_DUB = "dub"  # English only
FILE_SUB = "sub"  # no English track

# A show's files, regular seasons only.
SHOW_DUB = "dub"  # every file has English audio
SHOW_PART_DUB = "part_dub"
SHOW_SUB_ONLY = "sub_only"

_ENGLISH = frozenset({"eng", "en", "english"})
_UNKNOWN = frozenset({"", "und", "unknown", "mis", "zxx"})


def is_anime(details: dict[str, Any]) -> bool:
    """From Seerr's /tv or /movie details."""
    if any(k.get("id") == ANIME_KEYWORD_ID for k in details.get("keywords") or []):
        return True
    return details.get("originalLanguage") == "ja" and any(
        g.get("id") == ANIMATION_GENRE_ID for g in details.get("genres") or []
    )


async def async_audio_profiles(arr: Any) -> dict[str, int]:
    """The three profiles' ids on a Sonarr or Radarr, by choice. Missing ones
    are left out."""
    by_name = {p.get("name"): p["id"] for p in await arr._request("GET", "/qualityprofile") or []}
    return {choice: by_name[name] for choice, name in PROFILE_NAMES.items() if name in by_name}


def audio_choice(profile_id: int | None, profiles: dict[str, int]) -> str | None:
    """Which choice a series or film is on, or None if it's on another profile."""
    return next((choice for choice, pid in profiles.items() if pid == profile_id), None)


def _languages(value: str | None) -> list[str]:
    """Sonarr and Radarr join a file's track languages with "/" ("eng/jpn")."""
    return [part.strip().lower() for part in (value or "").split("/") if part.strip().lower() not in _UNKNOWN]


def file_audio(media_info: dict[str, Any] | None) -> str | None:
    """dual, dub or sub, or None if the file's tracks aren't tagged."""
    langs = _languages((media_info or {}).get("audioLanguages"))
    if not langs:
        return None
    english = any(lang in _ENGLISH for lang in langs)
    if not english:
        return FILE_SUB
    return FILE_DUAL if any(lang not in _ENGLISH for lang in langs) else FILE_DUB


def has_english_subs(media_info: dict[str, Any] | None) -> bool:
    return any(lang in _ENGLISH for lang in _languages((media_info or {}).get("subtitles")))


def has_english(media_info: dict[str, Any] | None) -> bool:
    return file_audio(media_info) in (FILE_DUAL, FILE_DUB)


def show_audio(files: list[dict[str, Any]]) -> str | None:
    """dub / part_dub / sub_only over a show's regular-season files; None if
    none of them says (no files, or untagged tracks)."""
    kinds = [file_audio(f.get("mediaInfo")) for f in files if (f.get("seasonNumber") or 0) > 0]
    known = [k for k in kinds if k is not None]
    if not known:
        return None
    english = sum(1 for k in known if k in (FILE_DUAL, FILE_DUB))
    if english == len(known):
        return SHOW_DUB
    return SHOW_PART_DUB if english else SHOW_SUB_ONLY


def is_dub_release(release: dict[str, Any]) -> bool:
    """A release Sonarr/Radarr scored as English audio (by name or indexer tag)."""
    return any(cf.get("name") in DUB_FORMATS for cf in release.get("customFormats") or [])
