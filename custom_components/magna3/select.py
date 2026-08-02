"""Select platform for the Grundfos MAGNA3 integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONTROL_MODES,
    DOMAIN,
    OPERATION_MODES,
    REG_ACTUAL_CONTROL_MODE,
    REG_ACTUAL_OPERATION_MODE,
    REG_CONTROL_MODE,
    REG_OPERATION_MODE,
)
from .entity import Magna3Entity
from .hub import Magna3Hub


@dataclass(frozen=True, kw_only=True)
class Magna3SelectEntityDescription(SelectEntityDescription):
    """Select description mapping an enum register pair."""

    write_register: int
    read_register: int
    enum: dict[int, str]


SELECT_TYPES: list[Magna3SelectEntityDescription] = [
    Magna3SelectEntityDescription(
        key="control_mode",
        translation_key="control_mode",
        icon="mdi:tune-variant",
        write_register=REG_CONTROL_MODE,
        read_register=REG_ACTUAL_CONTROL_MODE,
        enum=CONTROL_MODES,
    ),
    Magna3SelectEntityDescription(
        key="operation_mode",
        translation_key="operation_mode",
        icon="mdi:cog-outline",
        write_register=REG_OPERATION_MODE,
        read_register=REG_ACTUAL_OPERATION_MODE,
        enum=OPERATION_MODES,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up MAGNA3 selects."""
    hub: Magna3Hub = hass.data[DOMAIN][entry.entry_id]["hub"]
    async_add_entities(
        Magna3Select(hub, entry, description) for description in SELECT_TYPES
    )


class Magna3Select(Magna3Entity, SelectEntity):
    """Select writing an enum register; state follows the actual-value register."""

    entity_description: Magna3SelectEntityDescription

    def __init__(
        self,
        hub: Magna3Hub,
        entry: ConfigEntry,
        description: Magna3SelectEntityDescription,
    ) -> None:
        super().__init__(hub, entry, description.key)
        self.entity_description = description
        self._attr_options = list(description.enum.values())
        self._reverse_enum = {name: value for value, name in description.enum.items()}

    @property
    def current_option(self) -> str | None:
        raw = self._data_value(str(self.entity_description.read_register))
        if raw is None:
            return None
        return self.entity_description.enum.get(raw)

    @property
    def available(self) -> bool:
        return (
            super().available
            and self._data_value(str(self.entity_description.read_register)) is not None
        )

    async def async_select_option(self, option: str) -> None:
        self._ensure_remote_control()
        value = self._reverse_enum[option]
        if not await self.coordinator.async_write_register(
            self.entity_description.write_register, value
        ):
            self._raise_write_failed()
