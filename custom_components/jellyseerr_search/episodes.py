"""Episode picker: list a season's episodes in Sonarr, download chosen ones, and
choose whether new episodes download. Shared by the WebSocket commands."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .api import JellyseerrClient, JellyseerrError
from .audio import async_audio_profiles, file_audio, has_english_subs, is_anime
from .const import DOMAIN, EPISODE_WAIT_SECONDS
from .sonarr import SonarrClient, SonarrError, SonarrNotFoundError

_LOGGER = logging.getLogger(__name__)

# A show the picker added and nobody picked from is removed after this long, even
# if the card never said so (app closed, dashboard switched, phone asleep).
ADDED_GRACE = timedelta(hours=1)
STORAGE_VERSION = 1

# Followed shows. Sonarr itself searches once for an episode TVDB lists up to 14
# days after it aired (EpisodeRefreshedService), and its RSS sync catches releases
# posted later; but it unmonitors episodes listed over 14 days late
# (RefreshEpisodeService.UnmonitorReaddedEpisodes), which is usual for daily
# shows. So the sweep only steps in for those: aired since the show was followed,
# unmonitored, not removed through the card. It monitors and searches them, then
# retries every FOLLOW_RETRY for FOLLOW_GIVE_UP after its first search.
FOLLOW_FIRST_SEARCH = timedelta(hours=2)
FOLLOW_RETRY = timedelta(hours=6)
FOLLOW_GIVE_UP = timedelta(days=14)

EP_DOWNLOADED = "downloaded"
EP_DOWNLOADING = "downloading"
EP_WANTED = "wanted"
EP_NOT_AIRED = "not_aired"
EP_MISSING = "missing"


class AddedShows:
    """Sonarr series the picker added, with when, kept across restarts so the
    sweep can remove untouched ones."""

    def __init__(self, hass: HomeAssistant, entry_id: str, scope: str) -> None:
        # `scope` ties the ids to one Sonarr server (they mean nothing on another).
        self._store: Store[dict[str, str]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}.{scope}.added_shows"
        )
        self._added: dict[str, str] = {}

    async def async_load(self) -> None:
        self._added = await self._store.async_load() or {}

    def add(self, series_id: int) -> None:
        self._added[str(series_id)] = dt_util.utcnow().isoformat()
        self._store.async_delay_save(lambda: self._added, 1)

    def touch(self, series_id: int) -> None:
        """Still being looked at: restart its hour, so the sweep doesn't remove
        it from under a card that's open on it."""
        if str(series_id) in self._added:
            self.add(series_id)

    def forget(self, series_id: int) -> None:
        if self._added.pop(str(series_id), None) is not None:
            self._store.async_delay_save(lambda: self._added, 1)

    def due(self, now: datetime) -> list[int]:
        return [
            int(series_id)
            for series_id, when in self._added.items()
            if (added := dt_util.parse_datetime(when)) is None or now - added >= ADDED_GRACE
        ]


class FollowedShows:
    """Shows followed with "Get new episodes" from the card: since when, which
    episodes the sweep searched for (first and last time) and which the user
    removed through the card (never fetched again). Kept across restarts."""

    def __init__(self, hass: HomeAssistant, entry_id: str, scope: str) -> None:
        self._store: Store[dict[str, dict[str, Any]]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}.{scope}.followed_shows"
        )
        self._shows: dict[str, dict[str, Any]] = {}

    async def async_load(self) -> None:
        self._shows = await self._store.async_load() or {}

    def _save(self) -> None:
        self._store.async_delay_save(lambda: self._shows, 1)

    def follow(self, series_id: int) -> None:
        if str(series_id) not in self._shows:
            self._shows[str(series_id)] = {"since": dt_util.utcnow().isoformat(), "searched": {}, "removed": []}
            self._save()

    def unfollow(self, series_id: int) -> None:
        if self._shows.pop(str(series_id), None) is not None:
            self._save()

    def shows(self) -> dict[int, dict[str, Any]]:
        return {int(k): v for k, v in self._shows.items()}

    def removed(self, series_id: int, episode_ids: list[int]) -> None:
        """The user removed these through the card: don't fetch them again."""
        show = self._shows.get(str(series_id))
        if show is None:
            return
        show["removed"] = sorted(set(show.get("removed", [])) | set(episode_ids))
        self._save()

    def mark_searched(self, series_id: int, episode_ids: list[int], when: datetime) -> None:
        show = self._shows.get(str(series_id))
        if show is None:
            return
        searched = show.setdefault("searched", {})
        for episode_id in episode_ids:
            entry = searched.get(str(episode_id))
            first = entry["first"] if isinstance(entry, dict) else when.isoformat()
            searched[str(episode_id)] = {"first": first, "last": when.isoformat()}
        self._save()


class CheckedTypes:
    """Series whose type (Daily or not) a test search has confirmed, so later
    downloads skip the check (each one costs an indexer search)."""

    def __init__(self, hass: HomeAssistant, entry_id: str, scope: str) -> None:
        self._store: Store[dict[str, str]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}.{scope}.checked_types"
        )
        self._types: dict[str, str] = {}

    async def async_load(self) -> None:
        self._types = await self._store.async_load() or {}

    def confirmed(self, series_id: int, series_type: str | None) -> bool:
        return series_type is not None and self._types.get(str(series_id)) == series_type

    def confirm(self, series_id: int, series_type: str) -> None:
        if self._types.get(str(series_id)) != series_type:
            self._types[str(series_id)] = series_type
            self._store.async_delay_save(lambda: self._types, 1)


def due_followed_episodes(
    episodes: list[dict[str, Any]],
    since: datetime,
    searched: dict[str, dict[str, str]],
    removed: set[int],
    queued: set[int],
    now: datetime,
) -> list[dict[str, Any]]:
    """Episodes of a followed show the sweep should search for now.

    Regular seasons only; aired after the show was followed and at least
    FOLLOW_FIRST_SEARCH ago; not on disk, on the way, or removed by the user.
    New ones: only if unmonitored (Sonarr handles monitored ones itself). Ones
    already searched: again after FOLLOW_RETRY, until FOLLOW_GIVE_UP after the
    first search (counted from then, since late listings can be weeks old)."""
    due = []
    for ep in episodes:
        if (ep.get("seasonNumber") or 0) < 1 or ep.get("hasFile"):
            continue
        if ep["id"] in queued or ep["id"] in removed:
            continue
        aired = dt_util.parse_datetime(ep.get("airDateUtc") or "")
        if aired is None or aired < since or aired > now - FOLLOW_FIRST_SEARCH:
            continue
        entry = searched.get(str(ep["id"]))
        if not isinstance(entry, dict):
            if not ep.get("monitored"):
                due.append(ep)
            continue
        first = dt_util.parse_datetime(entry.get("first", ""))
        last = dt_util.parse_datetime(entry.get("last", ""))
        if first is None or last is None or now - first > FOLLOW_GIVE_UP or now - last < FOLLOW_RETRY:
            continue
        due.append(ep)
    return due


async def async_search_followed(sonarr: SonarrClient, followed: FollowedShows) -> None:
    """Fetch episodes of followed shows that Sonarr dropped because TVDB listed
    them more than 14 days after they aired (see FOLLOW_* above)."""
    now = dt_util.utcnow()
    for series_id, show in followed.shows().items():
        try:
            series = await sonarr.async_get_series(series_id)
            if not follows_new(series):
                followed.unfollow(series_id)  # Turned off, or changed in Sonarr.
                continue
            since = dt_util.parse_datetime(show.get("since", "")) or now
            due = due_followed_episodes(
                await sonarr.async_get_episodes(series_id),
                since,
                show.get("searched", {}),
                set(show.get("removed", [])),
                await sonarr.async_queued_episode_ids(series_id),
                now,
            )
            if not due:
                continue
            await sonarr.async_set_monitored([ep["id"] for ep in due if not ep.get("monitored")], True)
            await sonarr.async_search_episodes([ep["id"] for ep in due])
            followed.mark_searched(series_id, [ep["id"] for ep in due], now)
            _LOGGER.info("Searched %s late-listed episode(s) of followed series %s", len(due), series_id)
        except SonarrNotFoundError:
            followed.unfollow(series_id)  # Gone from Sonarr.
        except SonarrError as err:
            _LOGGER.debug("Couldn't check followed series %s: %s", series_id, err)


async def async_sweep_added(sonarr: SonarrClient, added: AddedShows) -> None:
    """Remove shows the picker added over an hour ago that are still untouched.
    A show with picks is kept and forgotten; a Sonarr error is retried next time."""
    for series_id in added.due(dt_util.utcnow()):
        try:
            result = await async_discard_show(sonarr, series_id)
        except HomeAssistantError as err:
            _LOGGER.debug("Couldn't check picker-added series %s: %s", series_id, err)
            continue
        added.forget(series_id)
        if result["removed"]:
            _LOGGER.info("Removed series %s: added by the episode picker, nothing picked", series_id)


_series_locks: dict[int, asyncio.Lock] = {}


def series_lock(series_id: int) -> asyncio.Lock:
    """One change at a time per series: the naming check can take a minute, and
    two overlapping changes (two taps, two users, the card and the sweep) must
    not interleave."""
    return _series_locks.setdefault(series_id, asyncio.Lock())


async def _set_type(sonarr: SonarrClient, series_id: int, series_type: str) -> dict[str, Any]:
    """Change only the series type, on a fresh copy, so nothing else Sonarr has
    (monitoring, seasons) is written back from an old one."""
    fresh = await sonarr.async_get_series(series_id)
    if fresh.get("seriesType") == series_type:
        return fresh
    return await sonarr.async_update_series({**fresh, "seriesType": series_type})


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
    seerr: JellyseerrClient, sonarr: SonarrClient, tvdb_id: int, anime: bool = False, audio: str | None = None
) -> dict[str, Any]:
    """Add the show where Seerr's requests would put it: its anime profile and
    folder for anime (Seerr does that only for its own requests), or the
    profile of the audio chosen on the card."""
    lookup = await sonarr.async_lookup(tvdb_id)
    if not lookup:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="not_on_tvdb",
            translation_placeholders={"tvdb_id": str(tvdb_id)},
        )
    profiles = await async_audio_profiles(sonarr) if audio is not None else {}
    if audio is not None and audio not in profiles:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="no_audio_profile")
    try:
        defaults = await seerr.async_get_sonarr_defaults(anime=anime or audio is not None)
    except JellyseerrError:
        defaults = None
    profile, root = defaults or await sonarr.async_first_profile_and_root()
    return await sonarr.async_add_series(lookup, profiles.get(audio, profile) if audio else profile, root)


async def _wait_for_episodes(sonarr: SonarrClient, series_id: int) -> None:
    """Until Sonarr has filled in the new show's episodes: some, and the same
    number twice in a row (it may still be inserting a long show)."""
    previous = -1
    for _ in range(EPISODE_WAIT_SECONDS):
        count = len(await sonarr.async_get_episodes(series_id))
        if count and count == previous:
            return
        previous = count
        await asyncio.sleep(1)


async def async_season_episodes(
    seerr: JellyseerrClient,
    sonarr: SonarrClient,
    tmdb_id: int,
    season_number: int,
    added_shows: AddedShows | None = None,
    audio: str | None = None,
) -> dict[str, Any]:
    """A season's episodes as Sonarr has them, with what audio each file has. A
    show Sonarr doesn't have is added first, with nothing monitored (Sonarr only
    lists episodes of shows it has); `added` tells the card to discard it if
    nothing gets picked."""
    try:
        details = await seerr.async_get_details("tv", tmdb_id)
    except JellyseerrError as err:
        raise _error("api_error", err) from err
    tvdb_id = (details.get("externalIds") or {}).get("tvdbId") or None
    if not tvdb_id:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="no_tvdb_id",
            translation_placeholders={"tmdb_id": str(tmdb_id)},
        )
    try:
        series = await sonarr.async_get_series_by_tvdb(tvdb_id)
        added = series is None
        if series is not None and added_shows is not None:
            added_shows.touch(series["id"])
        if series is None:
            series = await _add_to_sonarr(seerr, sonarr, tvdb_id, is_anime(details), audio)
            if added_shows is not None:
                added_shows.add(series["id"])
            await _wait_for_episodes(sonarr, series["id"])
            series = await sonarr.async_get_series(series["id"])
        episodes = await sonarr.async_get_episodes(series["id"], season_number)
        queued = await sonarr.async_queued_episode_ids(series["id"])
        files = (
            {f["id"]: f for f in await sonarr.async_get_episode_files(series["id"])}
            if any(ep.get("hasFile") for ep in episodes)
            else {}
        )
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
                # What the file's tracks are: dual, dub, sub, or None (no file, untagged).
                "audio": file_audio(media_info) if (media_info := (files.get(ep.get("episodeFileId")) or {}).get("mediaInfo")) else None,
                "english_subs": has_english_subs(media_info),
            }
            for ep in sorted(episodes, key=lambda e: e.get("episodeNumber") or 0)
        ],
    }


async def _fit_series_type(
    sonarr: SonarrClient, series: dict[str, Any], episode_id: int, checked: CheckedTypes | None = None
) -> tuple[dict[str, Any], str | None]:
    """Make the series type match how releases are named, by experiment.

    A Standard series rejects date-named releases ("Found daily-style episode for
    non-daily series") and a Daily one searches by air date only, so the wrong
    type means nothing is found. Air dates can't tell (a new daily show has two
    episodes), so search for one aired episode as the series is; if nothing
    matches, try the other type and keep it if that matches. Returns the series
    and the new type, or None if unchanged. Anime is left alone."""
    current = series.get("seriesType")
    if current not in ("standard", "daily"):
        return series, None
    if checked is not None and checked.confirmed(series["id"], current):
        return series, None
    if await sonarr.async_release_matches(episode_id):
        if checked is not None:
            checked.confirm(series["id"], current)
        return series, None
    other = "daily" if current == "standard" else "standard"
    series = await _set_type(sonarr, series["id"], other)
    try:
        matches = await sonarr.async_release_matches(episode_id)
    except SonarrError:
        # Don't leave it on a type nothing confirmed.
        await _set_type(sonarr, series["id"], current)
        raise
    if matches:
        if checked is not None:
            checked.confirm(series["id"], other)
        return series, other
    # Neither matches: nothing is out there yet. Put it back as it was.
    return await _set_type(sonarr, series["id"], current), None


async def _probe_episode(sonarr: SonarrClient, series_id: int, picked: list[int]) -> int | None:
    """The episode to test-search with: the latest aired pick still missing, or
    else the show's latest aired episode (so picking only future episodes, or
    following new ones, is checked too). Regular seasons only when there are
    any: specials are rarely on indexers, so testing one finds nothing either
    way and costs three searches (seen with The Apothecary Diaries, S00E54).
    None if nothing has aired."""
    now = dt_util.utcnow()
    aired = [ep for ep in await sonarr.async_get_episodes(series_id) if _aired(ep, now)]
    aired = [ep for ep in aired if (ep.get("seasonNumber") or 0) > 0] or aired
    preferred = [ep for ep in aired if ep["id"] in set(picked) and not ep.get("hasFile")]
    pool = preferred or aired
    return max(pool, key=lambda ep: ep.get("airDateUtc") or "")["id"] if pool else None


async def _download_episodes(
    sonarr: SonarrClient,
    series_id: int,
    episode_ids: list[int],
    added_shows: AddedShows | None = None,
    checked: CheckedTypes | None = None,
) -> dict[str, Any]:
    """Monitor the chosen episodes and search for them now. Episodes that haven't
    aired stay monitored and download when they do. The series type (Daily or
    not) is first checked against how releases are actually named."""
    type_changed = None
    try:
        series = await sonarr.async_get_series(series_id)
        # The most recent is the likeliest to be on the indexers.
        if (probe := await _probe_episode(sonarr, series_id, episode_ids)) is not None:
            series, type_changed = await _fit_series_type(sonarr, series, probe, checked)
        if not series.get("monitored"):
            # Seasons are unchanged, so this doesn't touch any episode.
            series = await sonarr.async_update_series({**series, "monitored": True})
        await sonarr.async_set_monitored(episode_ids, True)
        await sonarr.async_search_episodes(episode_ids)
    except SonarrNotFoundError as err:
        # Removed meanwhile (the sweep, another user, or by hand in Sonarr).
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="series_gone") from err
    except SonarrError as err:
        raise _error("sonarr_error", err) from err
    if added_shows is not None:
        added_shows.forget(series_id)  # Something was picked: keep it.
    return {**_show(series), "episode_ids": episode_ids, "series_type_changed": type_changed}


async def _set_show_options(
    sonarr: SonarrClient,
    series_id: int,
    follow_new: bool | None,
    daily: bool | None,
    added_shows: AddedShows | None = None,
    followed: FollowedShows | None = None,
    checked: CheckedTypes | None = None,
) -> dict[str, Any]:
    """Turn following new episodes on or off, and the Daily series type.

    Following works through the latest season's `monitored` flag. Changing it
    makes Sonarr set every episode in the season the same way, so episodes that
    have already aired are put back as they were: only future ones follow.
    Sonarr can't tell a future episode picked by hand from one monitored by
    following, so turning following off unmonitors both (the card says so)."""
    type_changed = None
    try:
        series = await sonarr.async_get_series(series_id)
        if follow_new and (probe := await _probe_episode(sonarr, series_id, [])) is not None:
            # Following new episodes is useless if their names won't match.
            series, type_changed = await _fit_series_type(sonarr, series, probe, checked)
            # The searches can take a while: work from what Sonarr has now.
            series = await sonarr.async_get_series(series_id)
        old_type = series.get("seriesType")
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
        if daily and old_type != "daily":
            # Sonarr doesn't search again when the type changes, so episodes
            # already wanted (searched by S/E number, found nothing) would stay
            # stuck. Search them by air date now.
            now = dt_util.utcnow()
            stuck = [
                ep["id"]
                for ep in await sonarr.async_get_episodes(series_id)
                if ep.get("monitored") and not ep.get("hasFile") and _aired(ep, now)
            ]
            await sonarr.async_search_episodes(stuck)
        if flips:
            now = dt_util.utcnow()
            aired = [
                ep
                for ep in await sonarr.async_get_episodes(series_id, latest["seasonNumber"])
                if _aired(ep, now) and ep["id"] in before
            ]
            await sonarr.async_set_monitored([e["id"] for e in aired if before[e["id"]]], True)
            await sonarr.async_set_monitored([e["id"] for e in aired if not before[e["id"]]], False)
    except SonarrNotFoundError as err:
        # Removed meanwhile (the sweep, another user, or by hand in Sonarr).
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="series_gone") from err
    except SonarrError as err:
        raise _error("sonarr_error", err) from err
    if follow_new and added_shows is not None:
        added_shows.forget(series_id)  # Following new episodes: keep it.
    if followed is not None and follow_new is not None:
        followed.follow(series_id) if follow_new else followed.unfollow(series_id)
    return {**_show(series), "series_type_changed": type_changed}


async def _discard_show(sonarr: SonarrClient, series_id: int) -> dict[str, Any]:
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


async def _remove_episodes(
    sonarr: SonarrClient,
    series_id: int,
    episode_ids: list[int],
    added_shows: AddedShows | None = None,
    seerr: JellyseerrClient | None = None,
    tmdb_id: int | None = None,
    followed: FollowedShows | None = None,
) -> dict[str, Any]:
    """Delete the files of downloaded episodes and unmonitor them, so Sonarr
    doesn't fetch them again. If nothing is left (no files, nothing monitored,
    not following new episodes), the show is removed from Sonarr too, and from
    Jellyseerr's records (which would otherwise say "partly available" until its
    nightly sync)."""
    try:
        episodes = await sonarr.async_get_episodes(series_id)
        chosen = {ep["id"] for ep in episodes if ep["id"] in set(episode_ids)}
        file_ids = sorted(
            {ep["episodeFileId"] for ep in episodes if ep["id"] in chosen and ep.get("hasFile") and ep.get("episodeFileId")}
        )
        # One file can hold two episodes: both lose it, so unmonitor both.
        affected = [ep["id"] for ep in episodes if ep["id"] in chosen or ep.get("episodeFileId") in file_ids]
        await sonarr.async_delete_episode_files(file_ids)
        await sonarr.async_set_monitored(affected, False)
        result = await _discard_show(sonarr, series_id)
    except SonarrNotFoundError as err:
        # Removed meanwhile (the sweep, another user, or by hand in Sonarr).
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="series_gone") from err
    except SonarrError as err:
        raise _error("sonarr_error", err) from err
    if followed is not None:
        followed.removed(series_id, affected)  # So following won't fetch them again.
    if added_shows is not None and result["removed"]:
        added_shows.forget(series_id)
    if result["removed"] and seerr is not None and tmdb_id:
        try:
            await seerr.async_forget("tv", tmdb_id, keep_requests=True)
        except JellyseerrError as err:
            # The files are gone either way; Jellyseerr catches up overnight.
            _LOGGER.warning("Removed from Sonarr, but Jellyseerr didn't forget TMDB %s: %s", tmdb_id, err)
    return {"series_id": series_id, "files_removed": len(file_ids), "show_removed": result["removed"]}


async def _series_for(
    seerr: JellyseerrClient, sonarr: SonarrClient, tmdb_id: int
) -> tuple[int | None, dict[str, Any] | None, bool]:
    """The show's TVDB id (from Jellyseerr), its Sonarr series if Sonarr has it,
    and whether it's anime."""
    details = await seerr.async_get_details("tv", tmdb_id)
    tvdb_id = (details.get("externalIds") or {}).get("tvdbId") or None
    return tvdb_id, (await sonarr.async_get_series_by_tvdb(tvdb_id) if tvdb_id else None), is_anime(details)


async def async_show_state(seerr: JellyseerrClient, sonarr: SonarrClient, tmdb_id: int) -> dict[str, Any]:
    """What the show page needs from Sonarr: whether it has the show and whether
    new episodes are followed. Never adds anything."""
    try:
        _, series, _ = await _series_for(seerr, sonarr, tmdb_id)
    except (JellyseerrError, SonarrError) as err:
        raise _error("sonarr_error", err) from err
    return {"in_sonarr": series is not None, "follow_new": bool(series and follows_new(series))}


async def async_follow_show(
    seerr: JellyseerrClient,
    sonarr: SonarrClient,
    tmdb_id: int,
    follow_new: bool,
    added_shows: AddedShows | None = None,
    followed: FollowedShows | None = None,
    checked: CheckedTypes | None = None,
    audio: str | None = None,
) -> dict[str, Any]:
    """Get new episodes on or off from the show page. A show Sonarr doesn't have
    is added first (nothing monitored, nothing searched), then followed; it's
    kept, since following is a reason to keep it."""
    try:
        tvdb_id, series, anime = await _series_for(seerr, sonarr, tmdb_id)
        if series is None:
            if not follow_new:
                return {"in_sonarr": False, "follow_new": False}
            if not tvdb_id:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="no_tvdb_id",
                    translation_placeholders={"tmdb_id": str(tmdb_id)},
                )
            series = await _add_to_sonarr(seerr, sonarr, tvdb_id, anime, audio)
            await _wait_for_episodes(sonarr, series["id"])
    except (JellyseerrError, SonarrError) as err:
        raise _error("sonarr_error", err) from err
    result = await async_set_show_options(
        sonarr, series["id"], follow_new, None, added_shows, followed, checked
    )
    return {**result, "in_sonarr": True}


# Public entry points: the same, one at a time per series (see series_lock).


async def async_download_episodes(sonarr: SonarrClient, series_id: int, *args: Any) -> dict[str, Any]:
    async with series_lock(series_id):
        return await _download_episodes(sonarr, series_id, *args)


async def async_set_show_options(sonarr: SonarrClient, series_id: int, *args: Any) -> dict[str, Any]:
    async with series_lock(series_id):
        return await _set_show_options(sonarr, series_id, *args)


async def async_discard_show(sonarr: SonarrClient, series_id: int) -> dict[str, Any]:
    async with series_lock(series_id):
        return await _discard_show(sonarr, series_id)


async def async_remove_episodes(sonarr: SonarrClient, series_id: int, *args: Any) -> dict[str, Any]:
    async with series_lock(series_id):
        return await _remove_episodes(sonarr, series_id, *args)


def files_status(episodes: list[dict[str, Any]], now: datetime) -> str | None:
    """available if every aired episode has a file, partially_available if
    some do, None if none do. Counted from the episodes, not Sonarr's
    percentOfEpisodes: that counts monitored episodes only, so 3 picked
    episodes of an aired 24 read as 100%."""
    if not any(ep.get("hasFile") for ep in episodes):
        return None
    if all(ep.get("hasFile") for ep in episodes if _aired(ep, now)):
        return "available"
    return "partially_available"


def show_files_status(episodes: list[dict[str, Any]], now: datetime) -> str | None:
    """files_status over the regular seasons (specials don't count)."""
    return files_status([ep for ep in episodes if ep.get("seasonNumber", 0) > 0], now)


def sonarr_season_status(season: dict[str, Any], episodes: list[dict[str, Any]], now: datetime) -> str:
    """A season's status in the card's terms, from its episodes in Sonarr."""
    status = files_status([ep for ep in episodes if ep.get("seasonNumber") == season["seasonNumber"]], now)
    if status:
        return status
    if season.get("monitored"):
        return "processing"  # wanted, nothing yet
    return "not_requested"


async def async_sonarr_seasons(
    seerr: JellyseerrClient, sonarr: SonarrClient, tmdb_id: int
) -> list[dict[str, Any]] | None:
    """The show's seasons as Sonarr numbers them (TVDB), which can differ from
    Jellyseerr's (TMDB: The Apothecary Diaries is one 60-episode season there,
    three on TVDB). From the series if Sonarr has it, else a lookup (adds
    nothing). None if Sonarr can't place the show."""
    tvdb_id, series, _ = await _series_for(seerr, sonarr, tmdb_id)
    if series is None and tvdb_id:
        series = await sonarr.async_lookup(tvdb_id)
    if series is None:
        return None
    episodes = await sonarr.async_get_episodes(series["id"]) if series.get("id") else []
    now = dt_util.utcnow()
    return [
        {
            "season_number": s["seasonNumber"],
            "name": f"Series {s['seasonNumber']}",
            "episode_count": (s.get("statistics") or {}).get("totalEpisodeCount", 0),
            "status": sonarr_season_status(s, episodes, now) if series.get("id") else "not_requested",
        }
        for s in sorted(series.get("seasons", []), key=lambda s: s["seasonNumber"])
        if s.get("seasonNumber", 0) > 0
    ]


async def async_request_seasons(
    seerr: JellyseerrClient,
    sonarr: SonarrClient,
    tmdb_id: int,
    seasons: list[int],
    added_shows: AddedShows | None = None,
    checked: CheckedTypes | None = None,
    audio: str | None = None,
) -> dict[str, Any]:
    """Get whole seasons, through Sonarr (its numbering): add the show if needed,
    check how it's released, monitor the seasons and search them."""
    try:
        tvdb_id, series, anime = await _series_for(seerr, sonarr, tmdb_id)
        if series is None:
            if not tvdb_id:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="no_tvdb_id",
                    translation_placeholders={"tmdb_id": str(tmdb_id)},
                )
            series = await _add_to_sonarr(seerr, sonarr, tvdb_id, anime, audio)
            await _wait_for_episodes(sonarr, series["id"])
        series_id = series["id"]
    except (JellyseerrError, SonarrError) as err:
        raise _error("sonarr_error", err) from err
    async with series_lock(series_id):
        try:
            now = dt_util.utcnow()
            wanted = set(seasons)
            in_seasons = [
                ep for ep in await sonarr.async_get_episodes(series_id)
                if ep.get("seasonNumber") in wanted and _aired(ep, now)
            ]
            type_changed = None
            if in_seasons:
                probe = max(in_seasons, key=lambda ep: ep.get("airDateUtc") or "")["id"]
                _, type_changed = await _fit_series_type(sonarr, await sonarr.async_get_series(series_id), probe, checked)
            fresh = await sonarr.async_get_series(series_id)
            # Monitoring a season monitors every episode in it (Sonarr's cascade).
            await sonarr.async_update_series({
                **fresh,
                "monitored": True,
                "seasons": [{**s, "monitored": True} if s["seasonNumber"] in wanted else s for s in fresh.get("seasons", [])],
            })
            for number in sorted(wanted):
                await sonarr._request("POST", "/command", json={"name": "SeasonSearch", "seriesId": series_id, "seasonNumber": number})
        except SonarrNotFoundError as err:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="series_gone") from err
        except SonarrError as err:
            raise _error("sonarr_error", err) from err
    if added_shows is not None:
        added_shows.forget(series_id)  # Requested: keep it.
    return {"series_id": series_id, "seasons": sorted(wanted), "series_type_changed": type_changed}
