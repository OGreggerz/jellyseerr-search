"""Actions: search Jellyseerr and request movies or shows."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
import homeassistant.helpers.config_validation as cv

from .api import JellyseerrClient, JellyseerrError
from .const import DOMAIN, MEDIA_TV, MEDIA_TYPES, REQUESTABLE_STATUSES

SERVICE_SEARCH = "search"
SERVICE_REQUEST = "request"
SERVICE_QUICK_REQUEST = "quick_request"

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_QUERY = "query"
ATTR_MEDIA_TYPE = "media_type"
ATTR_LIMIT = "limit"
ATTR_TMDB_ID = "tmdb_id"
ATTR_SEASONS = "seasons"
ATTR_IS_4K = "is_4k"

MEDIA_ALL = "all"


def parse_seasons(value: Any) -> list[int] | str:
    """Accept "all", a list of numbers, or a string like "1, 2, 5"."""
    if isinstance(value, str):
        if value.strip().lower() in ("", MEDIA_ALL):
            return MEDIA_ALL
        value = value.split(",")
    seasons = sorted({vol.Coerce(int)(str(part).strip()) for part in cv.ensure_list(value)})
    if not seasons or seasons[0] < 1:
        raise vol.Invalid("seasons must be 'all' or season numbers from 1 up")
    return seasons


_BASE = {vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string}

SEARCH_SCHEMA = vol.Schema(
    {
        **_BASE,
        vol.Required(ATTR_QUERY): vol.All(cv.string, vol.Length(min=1)),
        vol.Optional(ATTR_MEDIA_TYPE, default=MEDIA_ALL): vol.In((MEDIA_ALL, *MEDIA_TYPES)),
        vol.Optional(ATTR_LIMIT, default=10): vol.All(vol.Coerce(int), vol.Range(1, 20)),
    }
)
REQUEST_SCHEMA = vol.Schema(
    {
        **_BASE,
        vol.Required(ATTR_TMDB_ID): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Required(ATTR_MEDIA_TYPE): vol.In(MEDIA_TYPES),
        vol.Optional(ATTR_SEASONS, default=MEDIA_ALL): parse_seasons,
        vol.Optional(ATTR_IS_4K, default=False): cv.boolean,
    }
)
QUICK_REQUEST_SCHEMA = vol.Schema(
    {
        **_BASE,
        vol.Required(ATTR_QUERY): vol.All(cv.string, vol.Length(min=1)),
        vol.Optional(ATTR_MEDIA_TYPE, default=MEDIA_ALL): vol.In((MEDIA_ALL, *MEDIA_TYPES)),
    }
)


def resolve_client(hass: HomeAssistant, entry_id: str | None) -> JellyseerrClient:
    """The client for the chosen entry, or the only loaded one."""
    loaded = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]
    if entry_id:
        loaded = [entry for entry in loaded if entry.entry_id == entry_id]
        if not loaded:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="entry_not_loaded",
                translation_placeholders={"entry_id": entry_id},
            )
    if not loaded:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="no_server")
    if len(loaded) > 1:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="multiple_servers"
        )
    return loaded[0].runtime_data.client


async def async_search_media(
    client: JellyseerrClient, query: str, media_type: str, limit: int
) -> list[dict[str, Any]]:
    try:
        results = await client.async_search(query)
    except JellyseerrError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="api_error",
            translation_placeholders={"error": str(err)},
        ) from err
    if media_type != MEDIA_ALL:
        results = [item for item in results if item["media_type"] == media_type]
    return results[:limit]


async def async_trending_media(
    client: JellyseerrClient, media_type: str, limit: int
) -> list[dict[str, Any]]:
    try:
        results = await client.async_trending(media_type)
    except JellyseerrError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="api_error",
            translation_placeholders={"error": str(err)},
        ) from err
    # Seerr filters by type itself; older Jellyseerr releases may not.
    if media_type != MEDIA_ALL:
        results = [item for item in results if item["media_type"] == media_type]
    return results[:limit]


async def async_request_media(
    client: JellyseerrClient,
    media_type: str,
    tmdb_id: int,
    seasons: list[int] | str,
    is_4k: bool,
) -> dict[str, Any]:
    try:
        created = await client.async_request(media_type, tmdb_id, seasons, is_4k)
    except JellyseerrError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="request_failed",
            translation_placeholders={"error": str(err)},
        ) from err
    return {"request_id": (created or {}).get("id"), "tmdb_id": tmdb_id, "media_type": media_type}


async def async_tv_seasons(client: JellyseerrClient, tmdb_id: int) -> list[dict[str, Any]]:
    try:
        return await client.async_get_tv_seasons(tmdb_id)
    except JellyseerrError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="api_error",
            translation_placeholders={"error": str(err)},
        ) from err


@callback
def async_register_services(hass: HomeAssistant) -> None:
    async def search(call: ServiceCall) -> ServiceResponse:
        results = await async_search_media(
            resolve_client(hass, call.data.get(ATTR_CONFIG_ENTRY_ID)),
            call.data[ATTR_QUERY],
            call.data[ATTR_MEDIA_TYPE],
            call.data[ATTR_LIMIT],
        )
        return {"results": results}

    async def request(call: ServiceCall) -> ServiceResponse:
        seasons = call.data[ATTR_SEASONS] if call.data[ATTR_MEDIA_TYPE] == MEDIA_TV else MEDIA_ALL
        return await async_request_media(
            resolve_client(hass, call.data.get(ATTR_CONFIG_ENTRY_ID)),
            call.data[ATTR_MEDIA_TYPE],
            call.data[ATTR_TMDB_ID],
            seasons,
            call.data[ATTR_IS_4K],
        )

    async def quick_request(call: ServiceCall) -> ServiceResponse:
        """Request the top search hit. Made for voice: "request Dune"."""
        client = resolve_client(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        query = call.data[ATTR_QUERY]
        results = await async_search_media(client, query, call.data[ATTR_MEDIA_TYPE], 1)
        if not results:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="no_results",
                translation_placeholders={"query": query},
            )
        top = results[0]
        if top["status"] not in REQUESTABLE_STATUSES:
            # Already requested or on the server: report it rather than error.
            return {**top, "requested": False}
        await async_request_media(client, top["media_type"], top["tmdb_id"], MEDIA_ALL, False)
        return {**top, "requested": True}

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEARCH,
        search,
        schema=SEARCH_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REQUEST,
        request,
        schema=REQUEST_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_QUICK_REQUEST,
        quick_request,
        schema=QUICK_REQUEST_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

