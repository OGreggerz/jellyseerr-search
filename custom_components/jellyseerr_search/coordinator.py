"""Polls Jellyseerr's request counts for the sensors."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import JellyseerrAuthError, JellyseerrClient, JellyseerrError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .episodes import AddedShows, CheckedTypes, FollowedShows
from .radarr import RadarrClient
from .sonarr import SonarrClient

_LOGGER = logging.getLogger(__name__)

type JellyseerrConfigEntry = ConfigEntry[JellyseerrCoordinator]


class JellyseerrCoordinator(DataUpdateCoordinator[dict[str, int]]):
    """Owns the clients; `data` is the latest /request/count payload. `sonarr` is
    set only when the episode picker is configured in the options."""

    config_entry: JellyseerrConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: JellyseerrConfigEntry,
        client: JellyseerrClient,
        sonarr: SonarrClient | None = None,
        added_shows: AddedShows | None = None,
        followed: FollowedShows | None = None,
        checked: CheckedTypes | None = None,
        radarr: RadarrClient | None = None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client
        self.sonarr = sonarr
        self.added_shows = added_shows
        self.followed = followed
        self.checked = checked
        self.radarr = radarr

    async def _async_update_data(self) -> dict[str, int]:
        try:
            return await self.client.async_get_request_counts()
        except JellyseerrAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except JellyseerrError as err:
            raise UpdateFailed(str(err)) from err
