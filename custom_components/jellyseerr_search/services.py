"""Actions: search Jellyseerr and request movies or shows."""

from __future__ import annotations

import asyncio
from itertools import chain, zip_longest
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
from .const import (
    BROWSE_BRANDS,
    BROWSE_GENRE_MIN_VOTES,
    BROWSE_GENRES,
    BROWSE_MAX_PAGE,
    DOMAIN,
    MEDIA_TV,
    MEDIA_TYPES,
    REQUESTABLE_STATUSES,
)
from .coordinator import JellyseerrCoordinator
from .sonarr import SonarrClient, SonarrError

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
    return resolve_coordinator(hass, entry_id).client


def resolve_coordinator(hass: HomeAssistant, entry_id: str | None) -> JellyseerrCoordinator:
    """The coordinator for the chosen entry, or the only loaded one."""
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
    return loaded[0].runtime_data


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


async def async_library_media(client: JellyseerrClient, limit: int) -> list[dict[str, Any]]:
    """Movies and shows the server has, newest first."""
    try:
        return await client.async_library(limit)
    except JellyseerrError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="api_error",
            translation_placeholders={"error": str(err)},
        ) from err


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


async def async_popular_media(
    client: JellyseerrClient, media_type: str, limit: int
) -> list[dict[str, Any]]:
    """Popular titles. For "all", movies and shows alternate."""
    types = MEDIA_TYPES if media_type == MEDIA_ALL else (media_type,)
    try:
        lists = await asyncio.gather(*(client.async_popular(kind) for kind in types))
    except JellyseerrError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="api_error",
            translation_placeholders={"error": str(err)},
        ) from err
    mixed = [item for item in chain.from_iterable(zip_longest(*lists)) if item]
    return mixed[:limit]


async def async_discover_media(
    client: JellyseerrClient,
    media_type: str,
    *,
    provider: list[int],
    region: str,
    sort: str,
    genre: str | None,
    page: int,
    brand: str | None = None,
) -> dict[str, Any]:
    """One streaming service's titles (or any of several), a page at a time. For "all", a page of
    movies and a page of shows alternate. A genre or brand one type lacks
    (Horror has no TV genre, Pixar no TV filter) fetches only the other type."""
    ids = BROWSE_GENRES[genre] if genre else None
    by_brand = BROWSE_BRANDS[brand] if brand else None
    types = MEDIA_TYPES if media_type == MEDIA_ALL else (media_type,)
    kinds = [
        kind
        for kind in types
        if (ids is None or ids[kind]) and (by_brand is None or by_brand[kind])
    ]
    if not kinds:
        return {"results": [], "has_more": False}
    try:
        pages = await asyncio.gather(
            *(
                client.async_discover(
                    kind,
                    provider=provider,
                    region=region,
                    sort=sort,
                    genre=ids[kind] if ids else None,
                    brand=by_brand[kind] if by_brand else None,
                    min_votes=BROWSE_GENRE_MIN_VOTES.get(genre or ""),
                    page=page,
                )
                for kind in kinds
            )
        )
    except JellyseerrError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="api_error",
            translation_placeholders={"error": str(err)},
        ) from err
    mixed = [item for item in chain.from_iterable(zip_longest(*(r for r, _ in pages))) if item]
    last = [min(total, BROWSE_MAX_PAGE) for _, total in pages]
    return {"results": mixed, "has_more": any(page < end for end in last)}


async def async_remove_media(
    client: JellyseerrClient, media_type: str, tmdb_id: int, sonarr: SonarrClient | None = None
) -> dict[str, Any]:
    """Remove a title and its files. Through Jellyseerr when it has a record
    (it then marks the title deleted and keeps the request history); for a show
    it doesn't know yet (an episode-picker download before Jellyseerr's next
    scan), straight from Sonarr when that's set up."""
    try:
        removed = await client.async_remove(media_type, tmdb_id)
        if not removed and media_type == MEDIA_TV and sonarr is not None:
            removed = await _remove_from_sonarr(client, sonarr, tmdb_id)
    except SonarrError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="sonarr_error",
            translation_placeholders={"error": str(err)},
        ) from err
    except JellyseerrError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="remove_failed",
            translation_placeholders={"error": str(err)},
        ) from err
    if not removed:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="not_in_library",
            translation_placeholders={"tmdb_id": str(tmdb_id)},
        )
    return {"tmdb_id": tmdb_id, "media_type": media_type}


async def async_request_media(
    client: JellyseerrClient,
    media_type: str,
    tmdb_id: int,
    seasons: list[int] | str,
    is_4k: bool,
    profile_id: int | None = None,
) -> dict[str, Any]:
    try:
        created = await client.async_request(media_type, tmdb_id, seasons, is_4k, profile_id)
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


async def _remove_from_sonarr(client: JellyseerrClient, sonarr: SonarrClient, tmdb_id: int) -> bool:
    """Delete the show and its files from Sonarr. False if Sonarr hasn't got it."""
    tvdb_id = await client.async_get_tvdb_id(tmdb_id)
    series = await sonarr.async_get_series_by_tvdb(tvdb_id) if tvdb_id else None
    if series is None:
        return False
    await sonarr.async_delete_series(series["id"])
    return True


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

