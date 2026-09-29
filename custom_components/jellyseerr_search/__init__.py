"""The Jellyseerr Search integration."""

from __future__ import annotations

from homeassistant.const import CONF_API_KEY, CONF_URL, CONF_VERIFY_SSL, Platform
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import JellyseerrClient
from .const import DOMAIN
from .coordinator import JellyseerrConfigEntry, JellyseerrCoordinator
from .frontend import async_register_frontend
from .services import async_register_services
from .websocket import async_register_websocket

PLATFORMS: list[Platform] = [Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Once per HA process: register the actions, WS API and card."""
    async_register_services(hass)
    async_register_websocket(hass)
    await async_register_frontend(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: JellyseerrConfigEntry) -> bool:
    """Connect to one Jellyseerr server."""
    session = async_get_clientsession(hass, verify_ssl=entry.data.get(CONF_VERIFY_SSL, True))
    client = JellyseerrClient(session, entry.data[CONF_URL], entry.data[CONF_API_KEY])
    coordinator = JellyseerrCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: JellyseerrConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
