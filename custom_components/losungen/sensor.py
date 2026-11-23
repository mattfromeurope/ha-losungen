from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
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
    value_fn: Callable[[LosungDay], str]
    markdown_fn: Callable[[LosungDay], str] | None = None


def _truncate(text: str) -> str:
    if len(text) <= MAX_STATE_LENGTH:
        return text
    return text[: MAX_STATE_LENGTH - 1] + "…"


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
    coordinator: LosungenCoordinator = entry.runtime_data
    async_add_entities(
        LosungenSensor(coordinator, entry, description) for description in SENSORS
    )


class LosungenSensor(LosungenEntity, SensorEntity):
    entity_description: LosungenSensorDescription

    def __init__(
        self,
        coordinator: LosungenCoordinator,
        entry: ConfigEntry,
        description: LosungenSensorDescription,
    ) -> None:
        super().__init__(coordinator, entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def _today(self) -> LosungDay | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(dt_util.now().date().isoformat())

    @property
    def native_value(self) -> str | None:
        day = self._today
        if day is None:
            return None
        return _truncate(self.entity_description.value_fn(day))

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        day = self._today
        if day is None:
            return {}
        attributes = {
            ATTR_DATUM: day.date,
            ATTR_WOCHENTAG: day.weekday,
            ATTR_SONNTAG: day.sunday,
            ATTR_LOSUNGSTEXT: day.losungstext,
            ATTR_LOSUNGSVERS: day.losungsvers,
            ATTR_LEHRTEXT: day.lehrtext,
            ATTR_LEHRTEXTVERS: day.lehrtextvers,
        }
        if self.entity_description.markdown_fn is not None:
            attributes[ATTR_TEXT_MARKDOWN] = self.entity_description.markdown_fn(day)
        return attributes
