"""Episode picker: list a season's episodes in Sonarr, download chosen ones, and
choose whether new episodes download. Shared by the WebSocket commands."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.util import dt as dt_util

from .api import JellyseerrClient, JellyseerrError
from .const import DOMAIN, EPISODE_WAIT_SECONDS
from .sonarr import SonarrClient, SonarrError, SonarrNotFoundError

EP_DOWNLOADED = "downloaded"
EP_DOWNLOADING = "downloading"
EP_WANTED = "wanted"
EP_NOT_AIRED = "not_aired"
EP_MISSING = "missing"


def _error(key: str, err: Exception | None = None, **placeholders: str) -> HomeAssistantError:
    if err is not None:
        placeholders["error"] = str(err)
    return HomeAssistantError(
        translation_domain=DOMAIN, translation_key=key, translation_placeholders=placeholders
    )


def _aired(episode: dict[str, Any], now: datetime) -> bool:
    when = dt_util.parse_datetime(episode.get("airDateUtc") or "")
    return when is not None and when <= now


def episode_status(episode: dict[str, Any], queued: set[int], now: datetime) -> str:
    if episode.get("hasFile"):
        return EP_DOWNLOADED
    if episode["id"] in queued:
        return EP_DOWNLOADING
    if not _aired(episode, now):
        return EP_NOT_AIRED
    return EP_WANTED if episode.get("monitored") else EP_MISSING


def _latest_season(series: dict[str, Any]) -> dict[str, Any] | None:
    seasons = [s for s in series.get("seasons", []) if s.get("seasonNumber", 0) > 0]
    return max(seasons, key=lambda s: s["seasonNumber"]) if seasons else None


def follows_new(series: dict[str, Any]) -> bool:
    """New episodes download when the latest season is monitored (Sonarr monitors
    episodes added to a monitored season) and new seasons are monitored too."""
    latest = _latest_season(series)
    return series.get("monitorNewItems") == "all" and bool(latest and latest.get("monitored"))


def _show(series: dict[str, Any]) -> dict[str, Any]:
    return {
        "series_id": series["id"],
        "title": series.get("title", ""),
        "daily": series.get("seriesType") == "daily",
        "follow_new": follows_new(series),
    }


async def _add_to_sonarr(
    seerr: JellyseerrClient, sonarr: SonarrClient, tvdb_id: int
) -> dict[str, Any]:
    lookup = await sonarr.async_lookup(tvdb_id)
    if not lookup:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="not_on_tvdb",
            translation_placeholders={"tvdb_id": str(tvdb_id)},
        )
    try:
        defaults = await seerr.async_get_sonarr_defaults()
    except JellyseerrError:
        defaults = None
    profile, root = defaults or await sonarr.async_first_profile_and_root()
    return await sonarr.async_add_series(lookup, profile, root)


async def _wait_for_episodes(sonarr: SonarrClient, series_id: int) -> None:
    for _ in range(EPISODE_WAIT_SECONDS):
        if await sonarr.async_get_episodes(series_id):
            return
        await asyncio.sleep(1)


async def async_season_episodes(
    seerr: JellyseerrClient, sonarr: SonarrClient, tmdb_id: int, season_number: int
) -> dict[str, Any]:
    """A season's episodes as Sonarr has them. A show Sonarr doesn't have is added
    first, with nothing monitored (Sonarr only lists episodes of shows it has);
    `added` tells the card to discard it if nothing gets picked."""
    try:
        tvdb_id = await seerr.async_get_tvdb_id(tmdb_id)
    except JellyseerrError as err:
        raise _error("api_error", err) from err
    if not tvdb_id:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="no_tvdb_id",
            translation_placeholders={"tmdb_id": str(tmdb_id)},
        )
    try:
        series = await sonarr.async_get_series_by_tvdb(tvdb_id)
        added = series is None
        if series is None:
            series = await _add_to_sonarr(seerr, sonarr, tvdb_id)
            await _wait_for_episodes(sonarr, series["id"])
            series = await sonarr.async_get_series(series["id"])
        episodes = await sonarr.async_get_episodes(series["id"], season_number)
        queued = await sonarr.async_queued_episode_ids(series["id"])
    except SonarrError as err:
        raise _error("sonarr_error", err) from err
    now = dt_util.utcnow()
    return {
        **_show(series),
        "added": added,
        "season_number": season_number,
        "episodes": [
            {
                "id": ep["id"],
                "episode_number": ep.get("episodeNumber"),
                "title": ep.get("title") or "",
                "air_date": ep.get("airDate"),
                "status": episode_status(ep, queued, now),
                "monitored": bool(ep.get("monitored")),
            }
            for ep in sorted(episodes, key=lambda e: e.get("episodeNumber") or 0)
        ],
    }


async def async_download_episodes(
    sonarr: SonarrClient, series_id: int, episode_ids: list[int]
) -> dict[str, Any]:
    """Monitor the chosen episodes and search for them now. Episodes that haven't
    aired stay monitored and download when they do."""
    try:
        series = await sonarr.async_get_series(series_id)
        if not series.get("monitored"):
            # Seasons are unchanged, so this doesn't touch any episode.
            series = await sonarr.async_update_series({**series, "monitored": True})
        await sonarr.async_set_monitored(episode_ids, True)
        await sonarr.async_search_episodes(episode_ids)
    except SonarrError as err:
        raise _error("sonarr_error", err) from err
    return {**_show(series), "episode_ids": episode_ids}


async def async_set_show_options(
    sonarr: SonarrClient, series_id: int, follow_new: bool | None, daily: bool | None
) -> dict[str, Any]:
    """Turn following new episodes on or off, and the Daily series type.

    Following works through the latest season's `monitored` flag. Changing it
    makes Sonarr set every episode in the season the same way, so episodes that
    have already aired are put back as they were: only future ones follow.
    Sonarr can't tell a future episode picked by hand from one monitored by
    following, so turning following off unmonitors both (the card says so)."""
    try:
        series = await sonarr.async_get_series(series_id)
        update = {**series}
        if daily is not None:
            if daily:
                update["seriesType"] = "daily"
            elif series.get("seriesType") == "daily":
                update["seriesType"] = "standard"
        latest = _latest_season(series)
        before: dict[int, bool] = {}
        flips = follow_new is not None and latest is not None and bool(latest.get("monitored")) != follow_new
        if follow_new is not None:
            update["monitorNewItems"] = "all" if follow_new else "none"
            if follow_new:
                update["monitored"] = True
        if flips:
            before = {
                ep["id"]: bool(ep.get("monitored"))
                for ep in await sonarr.async_get_episodes(series_id, latest["seasonNumber"])
            }
            update["seasons"] = [
                {**s, "monitored": follow_new} if s["seasonNumber"] == latest["seasonNumber"] else s
                for s in series.get("seasons", [])
            ]
        series = await sonarr.async_update_series(update)
        if flips:
            now = dt_util.utcnow()
            aired = [
                ep
                for ep in await sonarr.async_get_episodes(series_id, latest["seasonNumber"])
                if _aired(ep, now) and ep["id"] in before
            ]
            await sonarr.async_set_monitored([e["id"] for e in aired if before[e["id"]]], True)
            await sonarr.async_set_monitored([e["id"] for e in aired if not before[e["id"]]], False)
    except SonarrError as err:
        raise _error("sonarr_error", err) from err
    return _show(series)


async def async_discard_show(sonarr: SonarrClient, series_id: int) -> dict[str, Any]:
    """Remove a show the picker added if nothing was picked: no files and no
    monitored episodes. Anything else is left alone."""
    try:
        series = await sonarr.async_get_series(series_id)
        files = (series.get("statistics") or {}).get("episodeFileCount", 0)
        monitored = any(ep.get("monitored") for ep in await sonarr.async_get_episodes(series_id))
        if files or monitored or follows_new(series):
            return {"series_id": series_id, "removed": False}
        await sonarr.async_delete_series(series_id)
    except SonarrNotFoundError:
        pass  # Already gone (removed in Sonarr, or by another discard).
    except SonarrError as err:
        raise _error("sonarr_error", err) from err
    return {"series_id": series_id, "removed": True}
