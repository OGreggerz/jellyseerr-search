"""The card's Waiting list: titles Sonarr or Radarr want but haven't got yet,
with whether each is out yet (release dates, next episode) and, on request,
whether copies are actually on the indexers."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from .animeschedule import DubSchedule
from .audio import (
    DUB_CHOICES,
    FILE_DUAL,
    FILE_DUB,
    SHOW_DUB,
    SHOW_SUB_ONLY,
    async_audio_profiles,
    audio_choice,
    file_audio,
    is_dub_release,
    show_audio,
)
from .const import DOMAIN, SEARCH_TIMEOUT
from .dubs import dub_wanted_episodes
from .episodes import show_files_status
from .radarr import RadarrClient, RadarrError
from .sonarr import SonarrClient, SonarrError

W_DOWNLOADING = "downloading"
W_NOT_FOUND = "not_found"  # out, wanted, nothing grabbed yet
W_NOT_OUT = "not_out"  # not released (film) or next episode not aired (TV)
W_DUB_WANTED = "dub_wanted"  # has the episodes, but not in English yet (dub profiles)

# How far ahead Sonarr's calendar is read for the next episode.
CALENDAR_DAYS = 120


def _poster(item: dict[str, Any]) -> str | None:
    for image in item.get("images") or []:
        if image.get("coverType") == "poster" and image.get("remoteUrl"):
            return image["remoteUrl"]
    return item.get("remotePoster") or None


def _day(value: str | None) -> str | None:
    """YYYY-MM-DD from Radarr's ISO timestamps (its release dates are whole days)."""
    return value[:10] if value else None


# Radarr's `status` (MovieStatusType): "released" only once a digital or physical
# release date has passed, or 90 days after the cinema date if there's neither
# (SkyHookProxy). `isAvailable` isn't used: it follows each film's minimum
# availability, and for "tba"/"announced" it's true before anything is out.
NOT_OUT_STATUSES = ("tba", "announced", "inCinemas")
CINEMA_TO_RELEASED = timedelta(days=90)


def film_state(movie: dict[str, Any], queued: set[int]) -> str:
    if movie["id"] in queued:
        return W_DOWNLOADING
    return W_NOT_OUT if movie.get("status") in NOT_OUT_STATUSES else W_NOT_FOUND


def expected_release(movie: dict[str, Any]) -> tuple[str | None, str | None]:
    """When Radarr will count the film as released, and why: the earlier of the
    digital and physical dates, otherwise the cinema date plus 90 days."""
    dated = [(d, kind) for d, kind in ((_day(movie.get("digitalRelease")), "digital"), (_day(movie.get("physicalRelease")), "physical")) if d]
    if dated:
        return min(dated)
    cinema = dt_util.parse_datetime(movie.get("inCinemas") or "")
    if cinema:
        return (cinema + CINEMA_TO_RELEASED).date().isoformat(), "cinema_plus_90"
    return None, None


async def _films(radarr: RadarrClient) -> list[dict[str, Any]]:
    movies, queued = await radarr.async_get_movies(), await radarr.async_queued_movie_ids()
    return [
        {
            "media_type": "movie",
            "tmdb_id": m.get("tmdbId") or None,
            "arr_id": m["id"],
            "title": m.get("title", ""),
            "year": m.get("year") or None,
            "poster_url": _poster(m),
            "state": film_state(m, queued),
            "release_status": m.get("status"),  # tba, announced, inCinemas, released
            "in_cinemas": _day(m.get("inCinemas")),
            "digital_release": _day(m.get("digitalRelease")),
            "physical_release": _day(m.get("physicalRelease")),
            "expected": expected_release(m)[0],
            "expected_basis": expected_release(m)[1],
            "last_search": m.get("lastSearchTime"),
        }
        for m in movies
        if m.get("monitored") and not m.get("hasFile")
    ]


async def _shows(sonarr: SonarrClient, now: datetime, schedule: DubSchedule | None = None) -> list[dict[str, Any]]:
    series = {s["id"]: s for s in await sonarr._request("GET", "/series") or []}
    # Anime on a dub profile waits for the dub too: episodes it has in Japanese.
    profiles = await async_audio_profiles(sonarr)
    audio = {sid: choice for sid, s in series.items() if (choice := audio_choice(s.get("qualityProfileId"), profiles))}
    dub_wanted: dict[int, int] = {}
    for sid, choice in audio.items():
        if choice in DUB_CHOICES and series[sid].get("monitored") and ((series[sid].get("statistics") or {}).get("episodeFileCount") or 0):
            count = len(dub_wanted_episodes(await sonarr.async_get_episodes(sid), await sonarr.async_get_episode_files(sid)))
            if count:
                dub_wanted[sid] = count
    missing = await sonarr._request(
        "GET", "/wanted/missing", params={"pageSize": 1000, "monitored": "true"}
    )
    missing_by_series: dict[int, list[dict[str, Any]]] = {}
    for ep in (missing or {}).get("records", []):
        missing_by_series.setdefault(ep["seriesId"], []).append(ep)
    calendar = await sonarr._request(
        "GET",
        "/calendar",
        params={
            "start": now.isoformat(),
            "end": (now + timedelta(days=CALENDAR_DAYS)).isoformat(),
            "unmonitored": "false",
        },
    )
    upcoming: dict[int, dict[str, Any]] = {}
    for ep in sorted(calendar or [], key=lambda e: e.get("airDateUtc") or ""):
        if ep.get("monitored") and not ep.get("hasFile"):
            upcoming.setdefault(ep["seriesId"], ep)
    queue = await sonarr._request("GET", "/queue", params={"pageSize": 1000})
    downloading = {r["seriesId"] for r in (queue or {}).get("records", []) if r.get("seriesId")}

    items = []
    for series_id in set(missing_by_series) | set(upcoming) | downloading | set(dub_wanted):
        s = series.get(series_id)
        if s is None or not s.get("monitored"):
            continue
        nxt = upcoming.get(series_id)
        state = (
            W_DOWNLOADING if series_id in downloading
            else W_NOT_FOUND if series_id in missing_by_series
            else W_NOT_OUT if nxt
            else W_DUB_WANTED
        )
        next_dub = None
        if schedule is not None and series_id in audio:
            names = [s.get("title")] + [t.get("title") for t in s.get("alternateTitles") or []]
            next_dub = await schedule.async_next_dub([n for n in names if n], now)
        items.append(
            {
                "media_type": "tv",
                "tmdb_id": s.get("tmdbId") or None,
                "arr_id": series_id,
                "title": s.get("title", ""),
                "year": s.get("year") or None,
                "poster_url": _poster(s),
                "state": state,
                "missing": len(missing_by_series.get(series_id, [])),
                "last_search": max(
                    (e.get("lastSearchTime") or "" for e in missing_by_series.get(series_id, [])), default=""
                ) or None,
                "next_episode": {
                    "season": nxt["seasonNumber"],
                    "episode": nxt["episodeNumber"],
                    "title": nxt.get("title") or "",
                    "air_date_utc": nxt.get("airDateUtc"),
                }
                if nxt
                else None,
                "audio": audio.get(series_id),
                "dub_wanted": dub_wanted.get(series_id, 0),
                "next_dub": next_dub,
            }
        )
    return items


def _sort_key(item: dict[str, Any]) -> tuple[int, str]:
    """Downloading, then out but not found, then not out (soonest first; no date
    last), then shows that only wait for a dub (often for months)."""
    rank = {W_DOWNLOADING: 0, W_NOT_FOUND: 1, W_NOT_OUT: 2, W_DUB_WANTED: 3}[item["state"]]
    if item["media_type"] == "tv":
        when = (item.get("next_episode") or {}).get("air_date_utc") or ""
    else:
        when = item.get("expected") or ""
    return rank, when or "9999"


async def async_waiting(
    sonarr: SonarrClient | None, radarr: RadarrClient | None, schedule: DubSchedule | None = None
) -> list[dict[str, Any]]:
    now = dt_util.utcnow()
    items: list[dict[str, Any]] = []
    try:
        if radarr is not None:
            items += await _films(radarr)
        if sonarr is not None:
            items += await _shows(sonarr, now, schedule)
    except (SonarrError, RadarrError) as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="sonarr_error", translation_placeholders={"error": str(err)}
        ) from err
    return sorted(items, key=_sort_key)


def summarise_releases(releases: list[dict[str, Any]], matches: Any) -> dict[str, Any]:
    """What an interactive search found for the title, in the app's own terms:
    how many releases matched it, how many it would take, the best one, and the
    commonest reasons it would turn the rest down (e.g. a cinema recording)."""
    matched = [r for r in releases if matches(r)]
    accepted = [r for r in matched if r.get("approved")]
    reasons: dict[str, int] = {}
    for r in matched:
        for reason in r.get("rejections") or []:
            text = reason if isinstance(reason, str) else str(reason.get("reason", reason))
            reasons[text] = reasons.get(text, 0) + 1
    best = accepted[0] if accepted else (matched[0] if matched else None)
    return {
        "found": len(matched),
        "accepted": len(accepted),
        # Of those it would take, how many it scored as English audio.
        "dubbed": sum(1 for r in accepted if is_dub_release(r)),
        "best": best.get("title") if best else None,
        "reasons": [text for text, _ in sorted(reasons.items(), key=lambda kv: -kv[1])[:3]],
        "checked_at": dt_util.utcnow().isoformat(),
    }


async def async_check(
    sonarr: SonarrClient | None, radarr: RadarrClient | None, media_type: str, arr_id: int
) -> dict[str, Any]:
    """Is a copy actually out there? Runs the app's interactive search (a live
    indexer search that grabs nothing; one hit per indexer). For a show, the
    oldest missing episode is checked, else the next one."""
    try:
        if media_type == "movie":
            if radarr is None:
                raise HomeAssistantError(translation_domain=DOMAIN, translation_key="no_radarr")
            releases = await radarr.async_releases(arr_id)
            return {**summarise_releases(releases, lambda r: True), "episode": None}
        if sonarr is None:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="no_sonarr")
        now = dt_util.utcnow()
        all_episodes = await sonarr.async_get_episodes(arr_id)
        episodes = [e for e in all_episodes if (e.get("seasonNumber") or 0) > 0 and not e.get("hasFile")]
        aired = sorted((e for e in episodes if e.get("airDateUtc") and dt_util.parse_datetime(e["airDateUtc"]) <= now and e.get("monitored")), key=lambda e: e["airDateUtc"])
        future = sorted((e for e in episodes if e.get("airDateUtc") and dt_util.parse_datetime(e["airDateUtc"]) > now), key=lambda e: e["airDateUtc"])
        # A show on a dub profile with every aired episode here: check the
        # oldest one still in Japanese instead.
        dubs = await _dub_wanted(sonarr, arr_id, all_episodes) if not aired else []
        target = (aired or sorted(dubs, key=lambda e: e.get("airDateUtc") or "") or future or [None])[0]
        if target is None:
            return {"found": 0, "accepted": 0, "dubbed": 0, "best": None, "reasons": [], "checked_at": now.isoformat(), "episode": None}
        releases = await sonarr._request("GET", "/release", params={"episodeId": target["id"]}, timeout=SEARCH_TIMEOUT)
        matches = lambda r: target["id"] in (r.get("episodeIds") or []) or any(m.get("id") == target["id"] for m in r.get("mappedEpisodeInfo") or [])
        return {
            **summarise_releases(releases or [], matches),
            "episode": {"season": target["seasonNumber"], "episode": target["episodeNumber"]},
        }
    except (SonarrError, RadarrError) as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="sonarr_error", translation_placeholders={"error": str(err)}
        ) from err


async def async_search_again(
    sonarr: SonarrClient | None, radarr: RadarrClient | None, media_type: str, arr_id: int
) -> None:
    """Ask the app to search for the title now (and grab if it finds one)."""
    try:
        if media_type == "movie":
            if radarr is None:
                raise HomeAssistantError(translation_domain=DOMAIN, translation_key="no_radarr")
            await radarr.async_search(arr_id)
        else:
            if sonarr is None:
                raise HomeAssistantError(translation_domain=DOMAIN, translation_key="no_sonarr")
            await sonarr._request("POST", "/command", json={"name": "MissingEpisodeSearch", "seriesId": arr_id})
            # Episodes still in Japanese aren't missing, so that skips them.
            if dubs := await _dub_wanted(sonarr, arr_id):
                await sonarr.async_search_episodes(sorted(e["id"] for e in dubs))
    except (SonarrError, RadarrError) as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="sonarr_error", translation_placeholders={"error": str(err)}
        ) from err


async def _dub_wanted(sonarr: SonarrClient, series_id: int, episodes: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Episodes of a series on a dub profile whose file isn't in English yet;
    empty for any other series."""
    profiles = await async_audio_profiles(sonarr)
    if not any(choice in profiles for choice in DUB_CHOICES):
        return []
    series = await sonarr.async_get_series(series_id)
    if audio_choice(series.get("qualityProfileId"), profiles) not in DUB_CHOICES:
        return []
    if episodes is None:
        episodes = await sonarr.async_get_episodes(series_id)
    return dub_wanted_episodes(episodes, await sonarr.async_get_episode_files(series_id))


# How long the Sonarr/Radarr view behind the result chips is reused. Changes made
# through the card clear it at once.
INDEX_TTL = timedelta(seconds=60)


class ArrIndex:
    """What Sonarr and Radarr have of each title, for the Downloaded / Waiting
    chips on search, browse and Downloaded results: downloaded = at least one
    file; waiting = in the Waiting list (wanted, not all here yet). A show with
    some episodes that's following new ones is both."""

    def __init__(self) -> None:
        self._data: dict[tuple[str, int], dict[str, Any]] | None = None
        self._built: datetime | None = None

    def invalidate(self) -> None:
        self._data = None

    async def async_get(
        self, sonarr: SonarrClient | None, radarr: RadarrClient | None
    ) -> dict[tuple[str, int], dict[str, Any]]:
        now = dt_util.utcnow()
        if self._data is not None and self._built and now - self._built < INDEX_TTL:
            return self._data
        waiting = {(i["media_type"], i["arr_id"]) for i in await async_waiting(sonarr, radarr)}
        data: dict[tuple[str, int], dict[str, Any]] = {}
        if sonarr is not None:
            # Dub / Part dub / Sub only, for anime on one of the audio profiles.
            profiles = await async_audio_profiles(sonarr)
            for s in await sonarr._request("GET", "/series") or []:
                has_files = ((s.get("statistics") or {}).get("episodeFileCount") or 0) > 0
                info: dict[str, Any] = {
                    "downloaded": has_files,
                    "waiting": ("tv", s["id"]) in waiting,
                }
                if has_files and audio_choice(s.get("qualityProfileId"), profiles):
                    info["audio"] = show_audio(await sonarr.async_get_episode_files(s["id"]))
                if s.get("tmdbId"):
                    data[("tv", s["tmdbId"])] = info
                if s.get("tvdbId"):
                    data[("tvdb", s["tvdbId"])] = info
        if radarr is not None:
            profiles = await async_audio_profiles(radarr)
            for m in await radarr.async_get_movies():
                if m.get("tmdbId"):
                    data[("movie", m["tmdbId"])] = {
                        "downloaded": bool(m.get("hasFile")),
                        "waiting": ("movie", m["id"]) in waiting,
                    }
                    kind = file_audio((m.get("movieFile") or {}).get("mediaInfo")) if m.get("hasFile") else None
                    if kind and audio_choice(m.get("qualityProfileId"), profiles):
                        data[("movie", m["tmdbId"])]["audio"] = SHOW_DUB if kind in (FILE_DUAL, FILE_DUB) else SHOW_SUB_ONLY
        self._data, self._built = data, now
        return data


async def async_annotate(
    results: list[dict[str, Any]], index: ArrIndex, sonarr: SonarrClient | None, radarr: RadarrClient | None
) -> list[dict[str, Any]]:
    """Add `arr` ({downloaded, waiting}) to results Sonarr/Radarr know. Never
    fails a search: if they can't be reached, results go out as they are."""
    if sonarr is None and radarr is None:
        return results
    try:
        data = await index.async_get(sonarr, radarr)
    except HomeAssistantError:
        return results
    for r in results:
        info = data.get((r["media_type"], r["tmdb_id"]))
        if info is None and r["media_type"] == "tv" and r.get("tvdb_id"):
            info = data.get(("tvdb", r["tvdb_id"]))
        if info is not None:
            r["arr"] = info
    return results


async def async_downloaded(
    sonarr: SonarrClient | None, radarr: RadarrClient | None, seerr_items: list[dict[str, Any]], limit: int
) -> list[dict[str, Any]]:
    """The Downloaded list from what Sonarr and Radarr actually have (the same
    source as the chips), newest file first. Jellyseerr's list lags: its Sonarr
    scan runs once a day, and its Jellyfin scan can't match a show whose seasons
    TMDB and TVDB number differently (The Apothecary Diaries). Titles only
    Jellyseerr knows (say, films with no Radarr set up) are kept after them."""
    waiting = {(i["media_type"], i["arr_id"]) for i in await async_waiting(sonarr, radarr)}
    by_tvdb = {i["tvdb_id"]: i for i in seerr_items if i["media_type"] == "tv" and i.get("tvdb_id")}
    items: list[dict[str, Any]] = []
    try:
        if radarr is not None:
            film_profiles = await async_audio_profiles(radarr)
            for m in await radarr.async_get_movies():
                if not m.get("hasFile"):
                    continue
                arr: dict[str, Any] = {"downloaded": True, "waiting": ("movie", m["id"]) in waiting}
                kind = file_audio((m.get("movieFile") or {}).get("mediaInfo"))
                if kind and audio_choice(m.get("qualityProfileId"), film_profiles):
                    arr["audio"] = SHOW_DUB if kind in (FILE_DUAL, FILE_DUB) else SHOW_SUB_ONLY
                items.append({
                    "tmdb_id": m.get("tmdbId") or None, "media_type": "movie", "title": m.get("title", ""),
                    "year": m.get("year") or None, "overview": m.get("overview") or "", "poster_url": _poster(m),
                    "status": "available", "tvdb_id": None,
                    "arr": arr,
                    "added": (m.get("movieFile") or {}).get("dateAdded") or "",
                })
        if sonarr is not None:
            show_profiles = await async_audio_profiles(sonarr)
            for s in await sonarr._request("GET", "/series") or []:
                stats = s.get("statistics") or {}
                if not stats.get("episodeFileCount"):
                    continue
                files = await sonarr._request("GET", "/episodefile", params={"seriesId": s["id"]}) or []
                episodes = await sonarr.async_get_episodes(s["id"]) or []
                seerr = by_tvdb.get(s.get("tvdbId"))
                items.append({
                    "tmdb_id": s.get("tmdbId") or (seerr or {}).get("tmdb_id"), "media_type": "tv",
                    "title": s.get("title", ""), "year": s.get("year") or None, "overview": s.get("overview") or "",
                    "poster_url": (seerr or {}).get("poster_url") or _poster(s),
                    "status": show_files_status(episodes, dt_util.utcnow()) or "partially_available",
                    "tvdb_id": s.get("tvdbId"),
                    "arr": {
                        "downloaded": True,
                        "waiting": ("tv", s["id"]) in waiting,
                        **({"audio": show_audio(files)} if audio_choice(s.get("qualityProfileId"), show_profiles) else {}),
                    },
                    "added": max((f.get("dateAdded") or "" for f in files), default=""),
                })
    except (SonarrError, RadarrError) as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="sonarr_error", translation_placeholders={"error": str(err)}
        ) from err
    items.sort(key=lambda i: i["added"], reverse=True)
    covered = {(i["media_type"], i["tmdb_id"]) for i in items} | {("tvdb", i["tvdb_id"]) for i in items if i["tvdb_id"]}
    extra = [
        i for i in seerr_items
        if (i["media_type"], i["tmdb_id"]) not in covered and ("tvdb", i.get("tvdb_id")) not in covered
        and not (i["media_type"] == "movie" and radarr is not None)  # Radarr is the truth for films
        and not (i["media_type"] == "tv" and sonarr is not None)  # and Sonarr for shows
    ]
    return [{k: v for k, v in i.items() if k != "added"} for i in items + extra][:limit]
