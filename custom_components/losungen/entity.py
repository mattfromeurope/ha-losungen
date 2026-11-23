"""Gemeinsame Basisklasse für alle Entities der Integration.

CoordinatorEntity koppelt eine Entity an den Coordinator: Sie ist automatisch
"available", solange der letzte Coordinator-Update erfolgreich war
(last_update_success), und wird nach jedem erfolgreichen Update neu
aktualisiert (HA ruft dann die Properties der Entity neu aus).
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME
from .coordinator import LosungenCoordinator


class LosungenEntity(CoordinatorEntity[LosungenCoordinator]):
    # has_entity_name=True: Der Anzeigename der Entity wird aus den
    # Übersetzungsdateien (translations/*.json, Schlüssel
    # entity.sensor.<translation_key>.name) genommen und dem Gerätenamen
    # vorangestellt, z. B. "Losungen Tageslosung".
    _attr_has_entity_name = True

    def __init__(self, coordinator: LosungenCoordinator, entry: ConfigEntry) -> None:
        # super().__init__ übernimmt den Coordinator und setzt die Verfügbarkeit.
        super().__init__(coordinator)
        # DeviceInfo gruppiert alle Sensoren dieser Integration unter einem Gerät
        # ("Losungen") in den HA-Geräten (Einstellungen -> Geräte & Dienste).
        self._attr_device_info = DeviceInfo(
            # identifiers: eindeutige Kennung des Geräts. (DOMAIN, entry_id)
            # koppelt das Gerät an genau diesen einen Config Entry.
            identifiers={(DOMAIN, entry.entry_id)},
            name=NAME,
            manufacturer="Evangelische Brüder-Unität (Herrnhuter Brüdergemeine)",
            # SERVICE: das "Gerät" repräsentiert einen Dienst, kein physisches Gerät.
            entry_type=DeviceEntryType.SERVICE,
            # Link, der in der Geräteansicht auf losungen.de verweist.
            configuration_url="https://www.losungen.de",
        )
