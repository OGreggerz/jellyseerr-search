"""Serve the card and register it as a Lovelace resource."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.core import HomeAssistant

from .const import CARD_URL, CARD_VERSION, URL_BASE

_LOGGER = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).parent / "frontend"
VERSIONED_CARD_URL = f"{CARD_URL}?v={CARD_VERSION}"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the card JS and add it to the dashboard resources."""
    # No cache headers: the version check in the card handles staleness.
    await hass.http.async_register_static_paths(
        [StaticPathConfig(URL_BASE, str(FRONTEND_DIR), False)]
    )
    try:
        await _async_register_resource(hass)
    except Exception:  # noqa: BLE001 - a missing resource must not break setup
        _LOGGER.warning(
            "Could not register the Jellyseerr Search card; add %s as a "
            "JavaScript module under Settings > Dashboards > Resources",
            VERSIONED_CARD_URL,
            exc_info=True,
        )


async def _async_register_resource(hass: HomeAssistant) -> None:
    """Add or update our resource entry. Storage-mode dashboards only."""
    lovelace: Any = hass.data.get("lovelace")
    # A dataclass on current HA; a plain dict before that.
    if isinstance(lovelace, dict):
        resources = lovelace.get("resources")
    else:
        resources = getattr(lovelace, "resources", None)
    if not isinstance(resources, ResourceStorageCollection):
        _LOGGER.info(
            "Lovelace resources are managed in YAML; add %s as a module resource",
            VERSIONED_CARD_URL,
        )
        return

    if not resources.loaded:
        await resources.async_load()
        resources.loaded = True

    ours = [
        item
        for item in resources.async_items()
        if item["url"].split("?", 1)[0] == CARD_URL
    ]
    if not ours:
        await resources.async_create_item(
            {"res_type": "module", "url": VERSIONED_CARD_URL}
        )
        return

    first, *duplicates = ours
    if first["url"] != VERSIONED_CARD_URL:
        await resources.async_update_item(
            first["id"], {"res_type": "module", "url": VERSIONED_CARD_URL}
        )
    for item in duplicates:
        await resources.async_delete_item(item["id"])
