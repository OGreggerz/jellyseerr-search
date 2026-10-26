"""The show or film page's audio choice: what a title is on (dub preferred, dub
only, Japanese + subtitles), what its files have, the next English dub date,
and changing the choice. TV through Sonarr, films through Radarr."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.util import dt as dt_util

from .animeschedule import DubSchedule
from .api import JellyseerrClient, JellyseerrError
from .audio import (
    AUDIO_DUB,
    DUB_CHOICES,
    FILE_DUAL,
    FILE_DUB,
    SHOW_DUB,
    SHOW_SUB_ONLY,
    async_audio_profiles,
    audio_choice,
    file_audio,
    has_english,
    is_anime,
    show_audio,
)
from .const import DOMAIN, MEDIA_MOVIE
from .episodes import series_lock
from .radarr import RadarrClient
from .sonarr import SonarrClient, SonarrError, SonarrNotFoundError

_LOGGER = logging.getLogger(__name__)


def _error(key: str, err: Exception | None = None) -> HomeAssistantError:
    return HomeAssistantError(
        translation_domain=DOMAIN,
        translation_key=key,
        translation_placeholders={"error": str(err)} if err is not None else None,
    )


def show_names(details: dict[str, Any], series: dict[str, Any] | None) -> list[str]:
    """Every name the show goes by, for matching AnimeSchedule's timetable."""
    names = [details.get("name"), details.get("originalName")]
    if series:
        names.append(series.get("title"))
        names += [t.get("title") for t in series.get("alternateTitles") or []]
    return [n for n in names if n]


def dub_wanted_episodes(episodes: list[dict[str, Any]], files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Monitored regular episodes whose file has no English audio. Untagged files
    don't count (they may well be dubbed)."""
    by_id = {f["id"]: f for f in files}
    wanted = []
    for ep in episodes:
        if (ep.get("seasonNumber") or 0) < 1 or not ep.get("monitored") or not ep.get("hasFile"):
            continue
        kind = file_audio((by_id.get(ep.get("episodeFileId")) or {}).get("mediaInfo"))
        if kind is not None and kind not in (FILE_DUAL, FILE_DUB):
            wanted.append(ep)
    return wanted


async def _tv_state(
    seerr: JellyseerrClient, sonarr: SonarrClient, tmdb_id: int, schedule: DubSchedule | None
) -> dict[str, Any]:
    details = await seerr.async_get_details("tv", tmdb_id)
    tvdb_id = (details.get("externalIds") or {}).get("tvdbId")
    series = await sonarr.async_get_series_by_tvdb(tvdb_id) if tvdb_id else None
    profiles = await async_audio_profiles(sonarr)
    choice = audio_choice(series.get("qualityProfileId"), profiles) if series else None
    anime = is_anime(details) or choice is not None
    state: dict[str, Any] = {
        "available": len(profiles) == 3,
        "anime": anime,
        "audio": choice,
        "in_arr": series is not None,
        "files": 0,
        "english_files": 0,
        "summary": None,
        "dub_wanted": 0,
        "dub": None,
        "dub_dates": schedule is not None,  # so "no date" can be told from "not looked"
    }
    if not anime:
        return state
    if series is not None:
        files = [f for f in await sonarr.async_get_episode_files(series["id"]) if (f.get("seasonNumber") or 0) > 0]
        state["files"] = len(files)
        state["english_files"] = sum(1 for f in files if has_english(f.get("mediaInfo")))
        state["summary"] = show_audio(files)
        if choice in DUB_CHOICES:
            state["dub_wanted"] = len(dub_wanted_episodes(await sonarr.async_get_episodes(series["id"]), files))
    if schedule is not None:
        state["dub"] = await schedule.async_next_dub(show_names(details, series))
    return state


async def _film_state(seerr: JellyseerrClient, radarr: RadarrClient, tmdb_id: int) -> dict[str, Any]:
    details = await seerr.async_get_details(MEDIA_MOVIE, tmdb_id)
    movie = await radarr.async_get_movie_by_tmdb(tmdb_id)
    profiles = await async_audio_profiles(radarr)
    choice = audio_choice(movie.get("qualityProfileId"), profiles) if movie else None
    kind = file_audio(((movie or {}).get("movieFile") or {}).get("mediaInfo")) if movie and movie.get("hasFile") else None
    english = kind in (FILE_DUAL, FILE_DUB)
    return {
        "available": len(profiles) == 3,
        "anime": is_anime(details) or choice is not None,
        "audio": choice,
        "in_arr": movie is not None,
        "files": 1 if kind else 0,
        "english_files": 1 if english else 0,
        "summary": None if kind is None else SHOW_DUB if english else SHOW_SUB_ONLY,
        "dub_wanted": 1 if kind is not None and not english and choice in DUB_CHOICES else 0,
        "dub": None,
        "dub_dates": False,  # AnimeSchedule's timetable is episodes only
    }


async def async_audio_state(
    seerr: JellyseerrClient,
    sonarr: SonarrClient | None,
    radarr: RadarrClient | None,
    media_type: str,
    tmdb_id: int,
    schedule: DubSchedule | None = None,
) -> dict[str, Any] | None:
    """The page's audio section, or None if the app it needs isn't set up."""
    try:
        if media_type == MEDIA_MOVIE:
            return await _film_state(seerr, radarr, tmdb_id) if radarr is not None else None
        return await _tv_state(seerr, sonarr, tmdb_id, schedule) if sonarr is not None else None
    except (JellyseerrError, SonarrError) as err:
        raise _error("sonarr_error", err) from err


async def async_profile_for(arr: SonarrClient | RadarrClient, audio: str) -> int:
    """The quality profile for an audio choice, or an error saying it's missing."""
    profiles = await async_audio_profiles(arr)
    if audio not in profiles:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="no_audio_profile")
    return profiles[audio]


async def async_anime_film_profile(seerr: JellyseerrClient, radarr: RadarrClient, tmdb_id: int, audio: str | None) -> int | None:
    """The Radarr profile a film request should carry: the chosen one, or for an
    anime film "dub preferred" (Seerr has no anime routing for films). None
    leaves Seerr's default."""
    if audio is not None:
        return await async_profile_for(radarr, audio)
    if not is_anime(await seerr.async_get_details(MEDIA_MOVIE, tmdb_id)):
        return None
    return (await async_audio_profiles(radarr)).get(AUDIO_DUB)


async def async_set_audio(
    seerr: JellyseerrClient,
    sonarr: SonarrClient | None,
    radarr: RadarrClient | None,
    media_type: str,
    tmdb_id: int,
    audio: str,
    schedule: DubSchedule | None = None,
) -> dict[str, Any]:
    """Move a title Sonarr or Radarr has to the choice's profile. Sonarr and
    Radarr don't search after a profile change, so for a dub choice the
    episodes (or film) without English audio, and missing aired ones, are
    searched now; RSS takes care of later posts."""
    try:
        if media_type == MEDIA_MOVIE:
            if radarr is None:
                raise ServiceValidationError(translation_domain=DOMAIN, translation_key="no_radarr")
            movie = await radarr.async_get_movie_by_tmdb(tmdb_id)
            if movie is None:
                raise ServiceValidationError(translation_domain=DOMAIN, translation_key="not_in_arr")
            profile = await async_profile_for(radarr, audio)
            if movie.get("qualityProfileId") != profile:
                await radarr.async_set_profile(movie["id"], profile)
            media_info = (movie.get("movieFile") or {}).get("mediaInfo")
            if audio in DUB_CHOICES and movie.get("monitored") and not (movie.get("hasFile") and has_english(media_info)):
                await radarr.async_search(movie["id"])
        else:
            if sonarr is None:
                raise ServiceValidationError(translation_domain=DOMAIN, translation_key="no_sonarr")
            tvdb_id = await seerr.async_get_tvdb_id(tmdb_id)
            series = await sonarr.async_get_series_by_tvdb(tvdb_id) if tvdb_id else None
            if series is None:
                raise ServiceValidationError(translation_domain=DOMAIN, translation_key="not_in_arr")
            profile = await async_profile_for(sonarr, audio)
            async with series_lock(series["id"]):
                fresh = await sonarr.async_get_series(series["id"])
                if fresh.get("qualityProfileId") != profile:
                    # Only the profile changes, on a fresh copy (as _set_type does).
                    await sonarr.async_update_series({**fresh, "qualityProfileId": profile})
                if audio in DUB_CHOICES:
                    episodes = await sonarr.async_get_episodes(series["id"])
                    now = dt_util.utcnow()
                    missing = [
                        ep for ep in episodes
                        if (ep.get("seasonNumber") or 0) > 0 and ep.get("monitored") and not ep.get("hasFile")
                        and (aired := dt_util.parse_datetime(ep.get("airDateUtc") or "")) is not None and aired <= now
                    ]
                    files = await sonarr.async_get_episode_files(series["id"])
                    targets = dub_wanted_episodes(episodes, files) + missing
                    await sonarr.async_search_episodes(sorted(ep["id"] for ep in targets))
                    if targets:
                        _LOGGER.info("Series %s now %s: searching %s episode(s) for a dub", series["id"], audio, len(targets))
    except SonarrNotFoundError as err:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="series_gone") from err
    except (JellyseerrError, SonarrError) as err:
        raise _error("sonarr_error", err) from err
    state = await async_audio_state(seerr, sonarr, radarr, media_type, tmdb_id, schedule)
    return state or {}
