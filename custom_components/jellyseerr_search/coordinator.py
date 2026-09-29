"""Polls Jellyseerr's request counts for the sensors."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import JellyseerrAuthError, JellyseerrClient, JellyseerrError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type JellyseerrConfigEntry = ConfigEntry[JellyseerrCoordinator]


class JellyseerrCoordinator(DataUpdateCoordinator[dict[str, int]]):
    """Owns the client; `data` is the latest /request/count payload."""

    config_entry: JellyseerrConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: JellyseerrConfigEntry, client: JellyseerrClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, int]:
        try:
            return await self.client.async_get_request_counts()
        except JellyseerrAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except JellyseerrError as err:
            raise UpdateFailed(str(err)) from err
