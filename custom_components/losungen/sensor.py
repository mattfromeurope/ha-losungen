"""Die vier Sensoren der Integration.

Jeder Sensor liest den heutigen Eintrag aus den Coordinator-Daten und stellt
einen der vier Werte als State bereit; der komplette Tagesdatensatz ist
zusätzlich als Attribute an jedem der vier Sensoren verfügbar.
"""

from __future__ import annotations

from collections.abc import Callable

# Callable[[LosungDay], str] ist der Typ "Funktion, die einen LosungDay nimmt
# und einen String zurückgibt" – damit sind die Wert-Funktionen unten typsicher.

from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription

# SensorEntity ist die Basisklasse für Sensoren; SensorEntityDescription ist das
# HA-Standardmuster, Entities über eine Beschreibung (key, icon, name ...) zu
# definieren.

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

# AddEntitiesCallback ist der Typ des Parameters, mit dem HA neue Entities
# an die Plattform übergibt.

from homeassistant.util import dt as dt_util

from .const import (
    ATTR_DATUM,
    ATTR_LEHRTEXT,
    ATTR_LEHRTEXTVERS,
    ATTR_LOSUNGSTEXT,
    ATTR_LOSUNGSVERS,
    ATTR_SONNTAG,
    ATTR_TEXT_MARKDOWN,
    ATTR_WOCHENTAG,
    MAX_STATE_LENGTH,
)
from .coordinator import LosungenCoordinator
from .entity import LosungenEntity
from .parser import LosungDay, markdown_text


@dataclass(frozen=True, kw_only=True)
class LosungenSensorDescription(SensorEntityDescription):
    """Sensor-Beschreibung um zwei Funktionen erweitert:

    value_fn:    Funktion, die aus dem LosungDay-Objekt den State-Wert holt
                 (z. B. lambda day: day.losungstext)
    markdown_fn: optional; erzeugt die Markdown-Variante des Textes, die als
                 Attribut text_markdown ausgegeben wird (nur bei Text-Sensoren)
    kw_only=True: beim Erzeugen müssen die Argumente mit Namen übergeben werden
                 (lesbarer, weniger fehleranfällig).
    """

    value_fn: Callable[[LosungDay], str]
    markdown_fn: Callable[[LosungDay], str] | None = None


def _truncate(text: str) -> str:
    """Kürzt einen Text auf die maximale State-Länge von HA (255 Zeichen).

    Home Assistant speichert Sensor-States nur bis 255 Zeichen; längere Texte
    (z. B. manche Lehrtexte) würden im State abgeschnitten. Der ungekürzte
    Text steht immer in den Attributen (siehe extra_state_attributes).
    """
    if len(text) <= MAX_STATE_LENGTH:
        return text  # passt komplett -> unverändert zurückgeben
    # Auf 254 Zeichen kürzen und "…" anhängen = exakt 255 Zeichen.
    return text[: MAX_STATE_LENGTH - 1] + "…"


# Definition der vier Sensoren. Pro Eintrag:
#  - key:             technischer Name, wird Teil der unique_id
#  - translation_key: verweist auf strings.json / translations/*.json
#                     (entity.sensor.<translation_key>.name = Anzeigename)
#  - icon:            MDI-Icon (https://pictogrammers.com/library/mdi/)
#  - value_fn:        holt den State aus dem LosungDay
#  - markdown_fn:     nur bei den Text-Sensoren: Markdown-Variante des Textes
SENSORS: tuple[LosungenSensorDescription, ...] = (
    LosungenSensorDescription(
        key="losungstext",
        translation_key="losungstext",
        icon="mdi:book-open-variant",
        value_fn=lambda day: day.losungstext,
        markdown_fn=lambda day: markdown_text(day.losungstext_raw),
    ),
    LosungenSensorDescription(
        key="losungsvers",
        translation_key="losungsvers",
        icon="mdi:bookmark-outline",
        value_fn=lambda day: day.losungsvers,
    ),
    LosungenSensorDescription(
        key="lehrtext",
        translation_key="lehrtext",
        icon="mdi:book-open-page-variant",
        value_fn=lambda day: day.lehrtext,
        markdown_fn=lambda day: markdown_text(day.lehrtext_raw),
    ),
    LosungenSensorDescription(
        key="lehrtextvers",
        translation_key="lehrtextvers",
        icon="mdi:bookmark-check-outline",
        value_fn=lambda day: day.lehrtextvers,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Wird von HA aufgerufen, wenn der Config Entry eingerichtet wird.

    HA ruft diese Funktion (über __init__.py -> async_forward_entry_setups)
    genau einmal pro Entry auf, nachdem der Coordinator die ersten Daten hat.
    """
    # Der Coordinator wurde in __init__.py in entry.runtime_data abgelegt.
    coordinator: LosungenCoordinator = entry.runtime_data
    # Generator-Ausdruck: für jede Sensor-Beschreibung eine Entity erzeugen und
    # alle auf einen Schlag an HA übergeben.
    async_add_entities(
        LosungenSensor(coordinator, entry, description) for description in SENSORS
    )


class LosungenSensor(LosungenEntity, SensorEntity):
    """Ein einzelner Losungen-Sensor (Text oder Bibelstelle).

    Erbt von LosungenEntity (Coordinator-Anbindung + Gerät) und SensorEntity
    (Sensor-Plattform). Das Verhalten steckt in den Properties native_value und
    extra_state_attributes, die HA bei jeder State-Abfrage neu auswertet.
    """

    entity_description: LosungenSensorDescription

    def __init__(
        self,
        coordinator: LosungenCoordinator,
        entry: ConfigEntry,
        description: LosungenSensorDescription,
    ) -> None:
        super().__init__(coordinator, entry)
        self.entity_description = description
        # unique_id macht die Entity eindeutig und persistent: Sie überlebt
        # Neustarts und Umbenennungen der Entity-ID. Aufbau: <entry_id>_<key>.
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def _today(self) -> LosungDay | None:
        """Liefert den LosungDay des heutigen Tages aus den Coordinator-Daten."""
        if not self.coordinator.data:
            return None  # noch keine Daten geladen (z. B. direkt nach dem Start)
        # Schlüssel im data-dict ist das ISO-Datum; "heute" in der lokalen
        # HA-Zeitzone – dasselbe Datum, das der Coordinator als Cache-Schlüssel
        # verwendet.
        return self.coordinator.data.get(dt_util.now().date().isoformat())

    @property
    def native_value(self) -> str | None:
        """Der State des Sensors – das, was `states('sensor...')` ausgibt."""
        day = self._today
        if day is None:
            return None  # HA zeigt dann "unknown" an
        # Wert über die konfigurierte Funktion holen und auf State-Länge kürzen.
        return _truncate(self.entity_description.value_fn(day))

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Attribute des Sensors: bei allen vier Sensoren der GANZE Tagesdatensatz.

        So kann eine Markdown-Card z. B. aus dem Bibelstellen-Sensor auch den
        Losungstext mit anzeigen, ohne einen zweiten Sensor abzufragen.
        """
        day = self._today
        if day is None:
            return {}
        attributes = {
            ATTR_DATUM: day.date,  # z. B. "2026-11-23"
            ATTR_WOCHENTAG: day.weekday,  # z. B. "Montag"
            ATTR_SONNTAG: day.sunday,  # liturgischer Sonntag, oft ""
            ATTR_LOSUNGSTEXT: day.losungstext,  # voller Text (unge­kürzt!)
            ATTR_LOSUNGSVERS: day.losungsvers,  # z. B. "Jesaja 55,10-11"
            ATTR_LEHRTEXT: day.lehrtext,  # voller Text (unge­kürzt!)
            ATTR_LEHRTEXTVERS: day.lehrtextvers,  # z. B. "Lukas 8,15"
        }
        if self.entity_description.markdown_fn is not None:
            # Nur die beiden Text-Sensoren haben eine Markdown-Funktion:
            # /.../ wird zu *...* (kursiv), #...# zu **...** (fett).
            attributes[ATTR_TEXT_MARKDOWN] = self.entity_description.markdown_fn(day)
        return attributes
