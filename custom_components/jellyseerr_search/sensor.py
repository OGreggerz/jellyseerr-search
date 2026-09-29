"""Request-count sensors: how many requests are pending, processing, and so on."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, REQUEST_COUNT_KEYS
from .coordinator import JellyseerrConfigEntry, JellyseerrCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JellyseerrConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(RequestCountSensor(coordinator, key) for key in REQUEST_COUNT_KEYS)


class RequestCountSensor(CoordinatorEntity[JellyseerrCoordinator], SensorEntity):
    """One field of GET /request/count."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "requests"
    _attr_icon = "mdi:movie-search"

    def __init__(self, coordinator: JellyseerrCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._key = key
        self._attr_translation_key = f"{key}_requests"
        self._attr_unique_id = f"{entry.entry_id}_{key}_requests"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Jellyseerr",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=entry.data["url"],
        )

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.get(self._key)
