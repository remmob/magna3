"""Base entity for the Grundfos MAGNA3 integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .hub import Magna3Hub


class Magna3Entity(CoordinatorEntity[Magna3Hub]):
    """Base class binding entities to the hub and the pump device."""

    _attr_has_entity_name = True

    def __init__(self, hub: Magna3Hub, entry: ConfigEntry, key: str) -> None:
        super().__init__(hub)
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        # No serial number register exists in the Grundfos Modbus profile for
        # the MAGNA3, so serial_number is only set when the hub reports one.
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Grundfos MAGNA 3",
            manufacturer="Mischa Bommer",
            model="Grundfos MAGNA 3",
            sw_version=hub.static_data.get("product_sw_version"),
            serial_number=hub.static_data.get("serial_number"),
        )

    def _data_value(self, key: str | None = None):
        data = self.coordinator.data or {}
        return data.get(key or self._key)

    def _ensure_remote_control(self) -> None:
        """Raise when the pump does not accept remote (Modbus) control."""
        if not self.coordinator.is_remote_controlled:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="not_remote_controlled",
            )

    @staticmethod
    def _raise_write_failed() -> None:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="write_failed",
        )
