"""Config Flow: Einrichtung der Integration über die Home-Assistant-Oberfläche.

Statt einer YAML-Konfiguration fügt der Nutzer die Integration unter
"Einstellungen -> Geräte & Dienste -> Hinzufügen -> Losungen" hinzu.
HA ruft dazu die Methode async_step_user() dieser Klasse auf.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

# ConfigFlow ist die HA-Basisklasse für UI-basierte Einrichtung;
# ConfigFlowResult ist der Rückgabetyp der Schritte (create_entry, abort, Formular ...).

from .const import DOMAIN


class LosungenConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config Flow der Domain "losungen".

    `domain=DOMAIN` in der Klassendeklaration verknüpft den Flow mit der
    Integration (HA erwartet die Klasse in config_flow.py, Name endet auf
    "ConfigFlow").
    """

    VERSION = 1
    # Version des Config-Entry-Datenschemas. Erhöhen, wenn sich der Inhalt von
    # entry.data je ändern sollte (dann ggf. Migration in __init__.py nötig).

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Erster (und einziger) Schritt: Formular ohne Eingabefelder.

        user_input ist None beim ersten Anzeigen des Formulars; da es keine
        Felder gibt, wird die Funktion danach direkt mit leeren Daten erneut
        aufgerufen und legt den Eintrag an.
        """
        # unique_id = DOMAIN: Es kann nur EINEN Config Entry dieser Integration
        # geben (die Daten sind ja global, nicht pro Instanz verschieden).
        await self.async_set_unique_id(DOMAIN)
        # Bricht mit "already_configured" ab, falls schon einer existiert.
        self._abort_if_unique_id_configured()
        # Config Entry anlegen: Titel "Losungen", data={} (keine Einstellungen nötig).
        # Der passende Text steht in strings.json / translations/*.json (config.step.user).
        return self.async_create_entry(title="Losungen", data={})
