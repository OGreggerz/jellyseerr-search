"""The Jellyseerr Search integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.const import CONF_API_KEY, CONF_URL, CONF_VERIFY_SSL, Platform
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType

from .api import JellyseerrClient
from .const import CONF_SONARR_API_KEY, CONF_SONARR_URL, DOMAIN
from .coordinator import JellyseerrConfigEntry, JellyseerrCoordinator
from .episodes import AddedShows, async_sweep_added
from .frontend import async_register_frontend
from .services import async_register_services
from .sonarr import SonarrClient
from .websocket import async_register_websocket

PLATFORMS: list[Platform] = [Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
SWEEP_INTERVAL = timedelta(minutes=15)


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
    sonarr = added_shows = None
    if entry.options.get(CONF_SONARR_URL) and entry.options.get(CONF_SONARR_API_KEY):
        sonarr = SonarrClient(
            async_get_clientsession(hass), entry.options[CONF_SONARR_URL], entry.options[CONF_SONARR_API_KEY]
        )
        added_shows = AddedShows(hass, entry.entry_id)
        await added_shows.async_load()
    coordinator = JellyseerrCoordinator(hass, entry, client, sonarr, added_shows)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    if sonarr is not None and added_shows is not None:
        # Shows the picker added but nobody picked from: the card removes them when
        # you leave the show, this catches the rest (app closed, phone asleep).
        async def _sweep(_now=None) -> None:
            await async_sweep_added(sonarr, added_shows)

        entry.async_on_unload(async_track_time_interval(hass, _sweep, SWEEP_INTERVAL))
        entry.async_create_background_task(hass, _sweep(), "jellyseerr_search sweep")
    return True


async def _async_options_updated(hass: HomeAssistant, entry: JellyseerrConfigEntry) -> None:
    """Sonarr was set up or removed in the options: reconnect."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: JellyseerrConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
