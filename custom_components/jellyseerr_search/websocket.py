"""WebSocket commands the search card uses."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from homeassistant.exceptions import ServiceValidationError

from .const import CARD_VERSION, DOMAIN, LIBRARY_LIMIT, MEDIA_TV, MEDIA_TYPES
from .episodes import (
    async_discard_show,
    async_download_episodes,
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
    ):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/version"})
@callback
def ws_version(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Lets the card spot a stale cached copy of itself."""
    connection.send_result(msg["id"], {"version": CARD_VERSION})


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
    # The card offers "Choose episodes" only when Sonarr is set up.
    connection.send_result(
        msg["id"], {"seasons": seasons, "episode_picker": coordinator.sonarr is not None}
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/request",
        vol.Required("tmdb_id"): vol.All(int, vol.Range(min=1)),
        vol.Required("media_type"): vol.In(MEDIA_TYPES),
        vol.Optional("seasons", default=MEDIA_ALL): parse_seasons,
        vol.Optional("is_4k", default=False): bool,
        vol.Optional("config_entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_request(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    client = resolve_client(hass, msg.get("config_entry_id"))
    seasons = msg["seasons"] if msg["media_type"] == MEDIA_TV else MEDIA_ALL
    result = await async_request_media(
        client, msg["media_type"], msg["tmdb_id"], seasons, msg["is_4k"]
    )
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
    client = resolve_client(hass, msg.get("config_entry_id"))
    result = await async_remove_media(client, msg["media_type"], msg["tmdb_id"])
    connection.send_result(msg["id"], result)


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
        vol.Optional("config_entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_episodes(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """A season's episodes from Sonarr. May add the show to Sonarr, unmonitored."""
    c = _picker(hass, msg.get("config_entry_id"))
    result = await async_season_episodes(
        c.client, c.sonarr, msg["tmdb_id"], msg["season_number"], c.added_shows
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
    result = await async_download_episodes(
        c.sonarr, msg["series_id"], msg["episode_ids"], c.added_shows, c.checked
    )
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
    result = await async_set_show_options(
        c.sonarr, msg["series_id"], msg.get("follow_new"), msg.get("daily"), c.added_shows, c.followed, c.checked
    )
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
    result = await async_remove_episodes(
        c.sonarr, msg["series_id"], msg["episode_ids"], c.added_shows, c.client, msg.get("tmdb_id"), c.followed
    )
    connection.send_result(msg["id"], result)
