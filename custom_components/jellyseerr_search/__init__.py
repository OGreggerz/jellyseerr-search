"""The Jellyseerr Search integration."""

from __future__ import annotations

from datetime import timedelta
import hashlib

from homeassistant.const import CONF_API_KEY, CONF_URL, CONF_VERIFY_SSL, Platform
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType

from .api import JellyseerrClient
from .const import CONF_RADARR_API_KEY, CONF_RADARR_URL, CONF_SONARR_API_KEY, CONF_SONARR_URL, DOMAIN
from .coordinator import JellyseerrConfigEntry, JellyseerrCoordinator
from .episodes import AddedShows, CheckedTypes, FollowedShows, async_search_followed, async_sweep_added
from .frontend import async_register_frontend
from .services import async_register_services
from .radarr import RadarrClient
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
    sonarr = added_shows = followed = checked = None
    if entry.options.get(CONF_SONARR_URL) and entry.options.get(CONF_SONARR_API_KEY):
        sonarr = SonarrClient(
            async_get_clientsession(hass), entry.options[CONF_SONARR_URL], entry.options[CONF_SONARR_API_KEY]
        )
        # Series ids only mean something on the Sonarr they came from.
        scope = hashlib.sha256(entry.options[CONF_SONARR_URL].encode()).hexdigest()[:8]
        added_shows = AddedShows(hass, entry.entry_id, scope)
        await added_shows.async_load()
        followed = FollowedShows(hass, entry.entry_id, scope)
        await followed.async_load()
        checked = CheckedTypes(hass, entry.entry_id, scope)
        await checked.async_load()
    radarr = None
    if entry.options.get(CONF_RADARR_URL) and entry.options.get(CONF_RADARR_API_KEY):
        radarr = RadarrClient(
            async_get_clientsession(hass), entry.options[CONF_RADARR_URL], entry.options[CONF_RADARR_API_KEY]
        )
    coordinator = JellyseerrCoordinator(hass, entry, client, sonarr, added_shows, followed, checked, radarr)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    if sonarr is not None and added_shows is not None and followed is not None:
        # Shows the picker added but nobody picked from: the card removes them when
        # you leave the show, this catches the rest (app closed, phone asleep).
        # Followed shows: search for new episodes Sonarr's RSS feed missed.
        async def _sweep(_now=None) -> None:
            await async_sweep_added(sonarr, added_shows)
            await async_search_followed(sonarr, followed)

        entry.async_on_unload(async_track_time_interval(hass, _sweep, SWEEP_INTERVAL))
        entry.async_create_background_task(hass, _sweep(), "jellyseerr_search sweep")
    return True


async def _async_options_updated(hass: HomeAssistant, entry: JellyseerrConfigEntry) -> None:
    """Sonarr was set up or removed in the options: reconnect."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: JellyseerrConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
