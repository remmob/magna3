"""Button platform for the Grundfos MAGNA3 integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import Magna3Entity
from .hub import Magna3Hub


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up MAGNA3 buttons."""
    hub: Magna3Hub = hass.data[DOMAIN][entry.entry_id]["hub"]
    async_add_entities([Magna3ResetAlarmButton(hub, entry)])


class Magna3ResetAlarmButton(Magna3Entity, ButtonEntity):
    """Reset pump alarms and warnings (ControlBits bit 2, rising edge)."""

    _attr_translation_key = "reset_alarm"
    _attr_icon = "mdi:alert-circle-check-outline"

    def __init__(self, hub: Magna3Hub, entry: ConfigEntry) -> None:
        super().__init__(hub, entry, "reset_alarm")

    async def async_press(self) -> None:
        self._ensure_remote_control()
        if not await self.coordinator.async_reset_alarm():
            self._raise_write_failed()
