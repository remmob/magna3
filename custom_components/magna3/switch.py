"""Switch platform for the Grundfos MAGNA3 integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONTROL_BIT_ENABLE_MAX_FLOW_LIMIT,
    CONTROL_BIT_ON_OFF,
    CONTROL_BIT_REMOTE_ACCESS,
    DOMAIN,
    STATUS_BIT_ACCESS_MODE,
    STATUS_BIT_MAX_FLOW_LIMIT_ENABLED,
    STATUS_BIT_ON_OFF,
    status_bit_key,
)
from .entity import Magna3Entity
from .hub import Magna3Hub


@dataclass(frozen=True, kw_only=True)
class Magna3SwitchEntityDescription(SwitchEntityDescription):
    """Switch description linking a control bit to a status bit."""

    control_bit: int
    status_bit: int
    requires_remote: bool = True


SWITCH_TYPES: list[Magna3SwitchEntityDescription] = [
    Magna3SwitchEntityDescription(
        key="remote_control",
        translation_key="remote_control",
        icon="mdi:remote",
        control_bit=CONTROL_BIT_REMOTE_ACCESS,
        status_bit=STATUS_BIT_ACCESS_MODE,
        requires_remote=False,
        entity_category=EntityCategory.CONFIG,
    ),
    Magna3SwitchEntityDescription(
        key="pump",
        translation_key="pump",
        icon="mdi:pump",
        control_bit=CONTROL_BIT_ON_OFF,
        status_bit=STATUS_BIT_ON_OFF,
    ),
    Magna3SwitchEntityDescription(
        key="flow_limit_enabled",
        translation_key="flow_limit_enabled",
        icon="mdi:water-check",
        control_bit=CONTROL_BIT_ENABLE_MAX_FLOW_LIMIT,
        status_bit=STATUS_BIT_MAX_FLOW_LIMIT_ENABLED,
        entity_category=EntityCategory.CONFIG,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up MAGNA3 switches."""
    hub: Magna3Hub = hass.data[DOMAIN][entry.entry_id]["hub"]
    async_add_entities(
        Magna3Switch(hub, entry, description) for description in SWITCH_TYPES
    )


class Magna3Switch(Magna3Entity, SwitchEntity):
    """Switch writing a ControlBits bit; state follows the StatusBits bit."""

    entity_description: Magna3SwitchEntityDescription

    def __init__(
        self,
        hub: Magna3Hub,
        entry: ConfigEntry,
        description: Magna3SwitchEntityDescription,
    ) -> None:
        super().__init__(hub, entry, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        value = self._data_value(status_bit_key(self.entity_description.status_bit))
        return None if value is None else bool(value)

    @property
    def available(self) -> bool:
        return (
            super().available
            and self._data_value(status_bit_key(self.entity_description.status_bit))
            is not None
        )

    async def _async_set(self, value: bool) -> None:
        if self.entity_description.requires_remote:
            self._ensure_remote_control()
        if not await self.coordinator.async_set_control_bit(
            self.entity_description.control_bit, value
        ):
            self._raise_write_failed()

    async def async_turn_on(self, **kwargs) -> None:
        await self._async_set(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._async_set(False)
