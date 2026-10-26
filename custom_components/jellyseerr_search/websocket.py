"""WebSocket commands the search card uses."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .const import CARD_VERSION, DOMAIN, LIBRARY_LIMIT, MEDIA_MOVIE, MEDIA_TV, MEDIA_TYPES
from .api import JellyseerrError
from .audio import AUDIO_CHOICES
from .dubs import async_anime_film_profile, async_audio_state, async_set_audio
from .sonarr import SonarrError
from .waiting import async_annotate, async_check, async_downloaded, async_search_again, async_waiting
from .episodes import (
    async_discard_show,
    async_download_episodes,
    async_follow_show,
    async_request_seasons,
    async_show_state,
    async_sonarr_seasons,
    async_remove_episodes,
    async_season_episodes,
    async_set_show_options,
)
from .services import (
    MEDIA_ALL,
    parse_seasons,
    async_request_media,
    async_search_media,
    async_library_media,
    async_popular_media,
    async_remove_media,
    async_trending_media,
    async_tv_seasons,
    resolve_client,
    resolve_coordinator,
)

SEARCH_LIMIT = 20


@callback
def async_register_websocket(hass: HomeAssistant) -> None:
    for command in (
        ws_version,
        ws_search,
        ws_trending,
        ws_popular,
        ws_library,
        ws_seasons,
        ws_request,
        ws_remove,
        ws_episodes,
        ws_episodes_download,
        ws_episodes_options,
        ws_episodes_discard,
        ws_episodes_remove,
        ws_episodes_follow,
        ws_episodes_request,
        ws_waiting,
        ws_release,
        ws_waiting_check,
        ws_waiting_search,
        ws_audio,
    ):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/version"})
@callback
def ws_version(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Lets the card spot a stale cached copy of itself, and whether the Waiting
    list has anything to read (Sonarr or Radarr set up)."""
    waiting = any(
        e.runtime_data.sonarr is not None or e.runtime_data.radarr is not None
        for e in hass.config_entries.async_loaded_entries(DOMAIN)
    )
    connection.send_result(msg["id"], {"version": CARD_VERSION, "waiting": waiting})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/search",
        vol.Required("query"): vol.All(str, vol.Length(min=1)),
        vol.Optional("media_type", default=MEDIA_ALL): vol.In((MEDIA_ALL, *MEDIA_TYPES)),
        vol.Optional("config_entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_search(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    client = resolve_client(hass, msg.get("config_entry_id"))
    results = await async_search_media(client, msg["query"], msg["media_type"], SEARCH_LIMIT)
    c = resolve_coordinator(hass, msg.get("config_entry_id"))
    results = await async_annotate(results, c.arr_index, c.sonarr, c.radarr)
    connection.send_result(msg["id"], {"results": results})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/trending",
        vol.Optional("media_type", default=MEDIA_ALL): vol.In((MEDIA_ALL, *MEDIA_TYPES)),
        vol.Optional("config_entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_trending(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """What the card shows before anything is typed."""
    client = resolve_client(hass, msg.get("config_entry_id"))
    results = await async_trending_media(client, msg["media_type"], SEARCH_LIMIT)
    c = resolve_coordinator(hass, msg.get("config_entry_id"))
    results = await async_annotate(results, c.arr_index, c.sonarr, c.radarr)
    connection.send_result(msg["id"], {"results": results})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/popular",
        vol.Optional("media_type", default=MEDIA_ALL): vol.In((MEDIA_ALL, *MEDIA_TYPES)),
        vol.Optional("config_entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_popular(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    client = resolve_client(hass, msg.get("config_entry_id"))
    results = await async_popular_media(client, msg["media_type"], SEARCH_LIMIT)
    c = resolve_coordinator(hass, msg.get("config_entry_id"))
    results = await async_annotate(results, c.arr_index, c.sonarr, c.radarr)
    connection.send_result(msg["id"], {"results": results})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/library",
        vol.Optional("config_entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_library(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """The card's Downloaded list: what the server already has, newest first."""
    client = resolve_client(hass, msg.get("config_entry_id"))
    results = await async_library_media(client, LIBRARY_LIMIT)
    c = resolve_coordinator(hass, msg.get("config_entry_id"))
    if c.sonarr is not None or c.radarr is not None:
        try:
            results = await async_downloaded(c.sonarr, c.radarr, results, LIBRARY_LIMIT)
        except HomeAssistantError:
            results = await async_annotate(results, c.arr_index, c.sonarr, c.radarr)  # *arr down: Jellyseerr's list
    else:
        results = await async_annotate(results, c.arr_index, c.sonarr, c.radarr)
    connection.send_result(msg["id"], {"results": results})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/seasons",
        vol.Required("tmdb_id"): vol.All(int, vol.Range(min=1)),
        vol.Optional("config_entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_seasons(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    coordinator = resolve_coordinator(hass, msg.get("config_entry_id"))
    seasons = await async_tv_seasons(coordinator.client, msg["tmdb_id"])
    result: dict[str, Any] = {"seasons": seasons, "episode_picker": coordinator.sonarr is not None}
    # The card offers "Episodes" and "Get new episodes" only when Sonarr is set up.
    if coordinator.sonarr is not None:
        try:
            result["show"] = await async_show_state(coordinator.client, coordinator.sonarr, msg["tmdb_id"])
        except HomeAssistantError:
            result["show"] = None  # Sonarr down: the seasons still show.
        # Sonarr's numbering, so the list, Episodes and Request match what
        # downloads (TMDB and TVDB can number a show's seasons differently).
        try:
            sonarr_seasons = await async_sonarr_seasons(coordinator.client, coordinator.sonarr, msg["tmdb_id"])
        except (JellyseerrError, SonarrError):
            sonarr_seasons = None
        if sonarr_seasons is not None:
            result["seasons"], result["season_source"] = sonarr_seasons, "sonarr"
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/request",
        vol.Required("tmdb_id"): vol.All(int, vol.Range(min=1)),
        vol.Required("media_type"): vol.In(MEDIA_TYPES),
        vol.Optional("seasons", default=MEDIA_ALL): parse_seasons,
        vol.Optional("is_4k", default=False): bool,
        vol.Optional("audio"): vol.In(AUDIO_CHOICES),
        vol.Optional("config_entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_request(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    c = resolve_coordinator(hass, msg.get("config_entry_id"))
    client = c.client
    seasons = msg["seasons"] if msg["media_type"] == MEDIA_TV else MEDIA_ALL
    # Films: Seerr has no anime routing for Radarr, so the profile goes with the
    # request (the audio chosen, or "dub preferred" for anime).
    profile_id = None
    if msg["media_type"] == MEDIA_MOVIE and c.radarr is not None and not msg["is_4k"]:
        try:
            profile_id = await async_anime_film_profile(client, c.radarr, msg["tmdb_id"], msg.get("audio"))
        except (JellyseerrError, SonarrError) as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="sonarr_error", translation_placeholders={"error": str(err)}
            ) from err
    result = await async_request_media(
        client, msg["media_type"], msg["tmdb_id"], seasons, msg["is_4k"], profile_id
    )
    # Downloaded / Waiting chips must show the change at once.
    resolve_coordinator(hass, msg.get("config_entry_id")).arr_index.invalidate()
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/remove",
        vol.Required("tmdb_id"): vol.All(int, vol.Range(min=1)),
        vol.Required("media_type"): vol.In(MEDIA_TYPES),
        vol.Optional("config_entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_remove(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Deletes files. The card only offers it when show_remove is set."""
    coordinator = resolve_coordinator(hass, msg.get("config_entry_id"))
    result = await async_remove_media(
        coordinator.client, msg["media_type"], msg["tmdb_id"], coordinator.sonarr
    )
    # Downloaded / Waiting chips must show the change at once.
    resolve_coordinator(hass, msg.get("config_entry_id")).arr_index.invalidate()
    connection.send_result(msg["id"], result)


async def _finish_regardless[T](hass: HomeAssistant, work: Awaitable[T]) -> T:
    """Run a change to completion even if the card goes away. HA cancels a
    command when its connection closes (the user leaves the screen or the app),
    which could stop the naming check between switching the series type and
    putting it back."""
    return await asyncio.shield(hass.async_create_task(work, "jellyseerr_search picker change"))


def _picker(hass: HomeAssistant, entry_id: str | None):
    coordinator = resolve_coordinator(hass, entry_id)
    if coordinator.sonarr is None:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="no_sonarr")
    return coordinator


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/episodes",
        vol.Required("tmdb_id"): vol.All(int, vol.Range(min=1)),
        vol.Required("season_number"): vol.All(int, vol.Range(min=0)),
        vol.Optional("audio"): vol.In(AUDIO_CHOICES),
        vol.Optional("config_entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_episodes(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """A season's episodes from Sonarr. May add the show to Sonarr, unmonitored
    (on the audio's profile, if one was chosen)."""
    c = _picker(hass, msg.get("config_entry_id"))
    result = await async_season_episodes(
        c.client, c.sonarr, msg["tmdb_id"], msg["season_number"], c.added_shows, msg.get("audio")
    )
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/episodes/download",
        vol.Required("series_id"): vol.All(int, vol.Range(min=1)),
        vol.Required("episode_ids"): vol.All([vol.All(int, vol.Range(min=1))], vol.Length(min=1)),
        vol.Optional("config_entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_episodes_download(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    c = _picker(hass, msg.get("config_entry_id"))
    result = await _finish_regardless(
        hass,
        async_download_episodes(c.sonarr, msg["series_id"], msg["episode_ids"], c.added_shows, c.checked),
    )
    # Downloaded / Waiting chips must show the change at once.
    resolve_coordinator(hass, msg.get("config_entry_id")).arr_index.invalidate()
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/episodes/options",
        vol.Required("series_id"): vol.All(int, vol.Range(min=1)),
        vol.Optional("follow_new"): bool,
        vol.Optional("daily"): bool,
        vol.Optional("config_entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_episodes_options(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Follow new episodes on/off, and the Daily series type (dated releases)."""
    c = _picker(hass, msg.get("config_entry_id"))
    result = await _finish_regardless(
        hass,
        async_set_show_options(
            c.sonarr, msg["series_id"], msg.get("follow_new"), msg.get("daily"), c.added_shows, c.followed, c.checked
        ),
    )
    # Downloaded / Waiting chips must show the change at once.
    resolve_coordinator(hass, msg.get("config_entry_id")).arr_index.invalidate()
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/episodes/discard",
        vol.Required("series_id"): vol.All(int, vol.Range(min=1)),
        vol.Optional("config_entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_episodes_discard(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """The card leaves a show it added without picking anything: remove it again,
    unless it has files or monitored episodes."""
    c = _picker(hass, msg.get("config_entry_id"))
    result = await async_discard_show(c.sonarr, msg["series_id"])
    if c.added_shows is not None:
        c.added_shows.forget(msg["series_id"])
    # Downloaded / Waiting chips must show the change at once.
    resolve_coordinator(hass, msg.get("config_entry_id")).arr_index.invalidate()
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/episodes/remove",
        vol.Required("series_id"): vol.All(int, vol.Range(min=1)),
        vol.Optional("tmdb_id"): vol.All(int, vol.Range(min=1)),
        vol.Required("episode_ids"): vol.All([vol.All(int, vol.Range(min=1))], vol.Length(min=1)),
        vol.Optional("config_entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_episodes_remove(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Deletes episode files. The card only offers it when show_remove is set."""
    c = _picker(hass, msg.get("config_entry_id"))
    result = await _finish_regardless(
        hass,
        async_remove_episodes(
            c.sonarr, msg["series_id"], msg["episode_ids"], c.added_shows, c.client, msg.get("tmdb_id"), c.followed
        ),
    )
    # Downloaded / Waiting chips must show the change at once.
    resolve_coordinator(hass, msg.get("config_entry_id")).arr_index.invalidate()
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/episodes/follow",
        vol.Required("tmdb_id"): vol.All(int, vol.Range(min=1)),
        vol.Required("follow_new"): bool,
        vol.Optional("audio"): vol.In(AUDIO_CHOICES),
        vol.Optional("config_entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_episodes_follow(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Get new episodes, from the show page. Adds the show to Sonarr if needed."""
    c = _picker(hass, msg.get("config_entry_id"))
    result = await _finish_regardless(
        hass,
        async_follow_show(
            c.client, c.sonarr, msg["tmdb_id"], msg["follow_new"], c.added_shows, c.followed, c.checked,
            msg.get("audio"),
        ),
    )
    # Downloaded / Waiting chips must show the change at once.
    resolve_coordinator(hass, msg.get("config_entry_id")).arr_index.invalidate()
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/waiting", vol.Optional("config_entry_id"): str}
)
@websocket_api.async_response
async def ws_waiting(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Titles Sonarr/Radarr want but haven't got, with whether each is out yet."""
    c = resolve_coordinator(hass, msg.get("config_entry_id"))
    if c.sonarr is None and c.radarr is None:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="no_arr")
    connection.send_result(msg["id"], {"results": await async_waiting(c.sonarr, c.radarr, c.schedule)})


_ARR_ITEM = {
    vol.Required("media_type"): vol.In(MEDIA_TYPES),
    vol.Required("arr_id"): vol.All(int, vol.Range(min=1)),
    vol.Optional("config_entry_id"): str,
}


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/waiting/check", **_ARR_ITEM})
@websocket_api.async_response
async def ws_waiting_check(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Is a copy out there? An interactive search: one indexer hit, grabs nothing."""
    c = resolve_coordinator(hass, msg.get("config_entry_id"))
    connection.send_result(msg["id"], await async_check(c.sonarr, c.radarr, msg["media_type"], msg["arr_id"]))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/waiting/search", **_ARR_ITEM})
@websocket_api.async_response
async def ws_waiting_search(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Search now, and grab what the app's rules accept."""
    c = resolve_coordinator(hass, msg.get("config_entry_id"))
    await async_search_again(c.sonarr, c.radarr, msg["media_type"], msg["arr_id"])
    # Downloaded / Waiting chips must show the change at once.
    resolve_coordinator(hass, msg.get("config_entry_id")).arr_index.invalidate()
    connection.send_result(msg["id"], {"searching": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/release",
        vol.Required("tmdb_id"): vol.All(int, vol.Range(min=1)),
        vol.Required("media_type"): vol.In(MEDIA_TYPES),
        vol.Optional("config_entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_release(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Is it out yet? TMDB's dates, for the line under a title's name."""
    client = resolve_client(hass, msg.get("config_entry_id"))
    try:
        info = await client.async_release_info(msg["media_type"], msg["tmdb_id"])
    except JellyseerrError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="api_error", translation_placeholders={"error": str(err)}
        ) from err
    connection.send_result(msg["id"], info)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/episodes/request",
        vol.Required("tmdb_id"): vol.All(int, vol.Range(min=1)),
        vol.Required("seasons"): vol.All([vol.All(int, vol.Range(min=1))], vol.Length(min=1)),
        vol.Optional("audio"): vol.In(AUDIO_CHOICES),
        vol.Optional("config_entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_episodes_request(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Request whole seasons through Sonarr (its numbering)."""
    c = _picker(hass, msg.get("config_entry_id"))
    result = await _finish_regardless(
        hass,
        async_request_seasons(
            c.client, c.sonarr, msg["tmdb_id"], msg["seasons"], c.added_shows, c.checked, msg.get("audio")
        ),
    )
    c.arr_index.invalidate()
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/audio",
        vol.Required("tmdb_id"): vol.All(int, vol.Range(min=1)),
        vol.Required("media_type"): vol.In(MEDIA_TYPES),
        vol.Optional("audio"): vol.In(AUDIO_CHOICES),
        vol.Optional("config_entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_audio(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """The page's audio section: anime or not, dub or sub chosen, what the files
    have, the next dub date. With `audio`, changes it first (and searches for
    dubs). `null` when Sonarr (shows) or Radarr (films) isn't set up."""
    c = resolve_coordinator(hass, msg.get("config_entry_id"))
    if "audio" in msg:
        state = await _finish_regardless(
            hass, async_set_audio(c.client, c.sonarr, c.radarr, msg["media_type"], msg["tmdb_id"], msg["audio"], c.schedule)
        )
        c.arr_index.invalidate()
    else:
        state = await async_audio_state(c.client, c.sonarr, c.radarr, msg["media_type"], msg["tmdb_id"], c.schedule)
    connection.send_result(msg["id"], state)
