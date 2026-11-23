"""Einstiegspunkt der Integration.

Home Assistant lädt beim Start für jeden Config Entry async_setup_entry() und
beim Entladen async_unload_entry(). Hier wird der Coordinator erzeugt, mit den
ersten Daten befüllt und die Sensor-Plattform gestartet.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import LosungenCoordinator

# Liste der Plattformen, die diese Integration bereitstellt – hier nur Sensoren.
# Plattformen werden als Modul unter custom_components/losungen/<plattform>.py
# erwartet (also sensor.py).
PLATFORMS: list[Platform] = [Platform.SENSOR]

# Typ-Alias: ein ConfigEntry, dessen runtime_data unser Coordinator ist.
# `type X = ...` ist die moderne Syntax (Python 3.12+) für Typ-Aliase; sie
# hilft Typcheckern, entry.runtime_data korrekt zu tippen.
type LosungenConfigEntry = ConfigEntry[LosungenCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: LosungenConfigEntry) -> bool:
    """Wird einmal pro Config Entry aufgerufen (beim Start bzw. nach dem Hinzufügen)."""
    # Coordinator anlegen (achtet selbst auf sein Poll-Intervall).
    coordinator = LosungenCoordinator(hass)
    # Erste Daten sofort laden. Schlägt das fehl (UpdateFailed), wirft HA
    # ConfigEntryNotReady und versucht es automatisch später erneut (Retry).
    await coordinator.async_config_entry_first_refresh()
    # Coordinator im Config Entry speichern, damit die Plattformen (sensor.py)
    # über entry.runtime_data darauf zugreifen können.
    entry.runtime_data = coordinator
    # Plattformen einrichten: HA ruft jetzt sensor.py:async_setup_entry() auf.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True  # True = Einrichtung erfolgreich


async def async_unload_entry(hass: HomeAssistant, entry: LosungenConfigEntry) -> bool:
    """Entlädt die Plattformen wieder (z. B. wenn die Integration entfernt wird)."""
    # Gibt True zurück, wenn alle Plattformen sauber entladen wurden.
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
