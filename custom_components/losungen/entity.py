from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME
from .coordinator import LosungenCoordinator


class LosungenEntity(CoordinatorEntity[LosungenCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: LosungenCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=NAME,
            manufacturer="Evangelische Brüder-Unität (Herrnhuter Brüdergemeine)",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://www.losungen.de",
        )
