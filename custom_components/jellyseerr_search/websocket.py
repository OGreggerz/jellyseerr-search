"""WebSocket commands the search card uses."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import CARD_VERSION, DOMAIN, MEDIA_TV, MEDIA_TYPES
from .services import (
    MEDIA_ALL,
    parse_seasons,
    async_request_media,
    async_search_media,
    async_popular_media,
    async_trending_media,
    async_tv_seasons,
    resolve_client,
)

SEARCH_LIMIT = 20


@callback
def async_register_websocket(hass: HomeAssistant) -> None:
    for command in (ws_version, ws_search, ws_trending, ws_popular, ws_seasons, ws_request):
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
        vol.Required("type"): f"{DOMAIN}/seasons",
        vol.Required("tmdb_id"): vol.All(int, vol.Range(min=1)),
        vol.Optional("config_entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_seasons(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    client = resolve_client(hass, msg.get("config_entry_id"))
    seasons = await async_tv_seasons(client, msg["tmdb_id"])
    connection.send_result(msg["id"], {"seasons": seasons})


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
