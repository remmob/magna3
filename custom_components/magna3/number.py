"""Number platform for the Grundfos MAGNA3 integration."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfVolumeFlowRate
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, REG_MAX_FLOW_LIMIT, REG_SETPOINT
from .entity import Magna3Entity
from .hub import Magna3Hub


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up MAGNA3 numbers."""
    hub: Magna3Hub = hass.data[DOMAIN][entry.entry_id]["hub"]
    async_add_entities([Magna3Setpoint(hub, entry), Magna3MaxFlowLimit(hub, entry)])


class Magna3Setpoint(Magna3Entity, NumberEntity):
    """Pump setpoint in percent (register 00104, actual from 00338)."""

    _attr_translation_key = "setpoint"
    _attr_icon = "mdi:target"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_native_step = 0.5
    _attr_mode = NumberMode.SLIDER

    def __init__(self, hub: Magna3Hub, entry: ConfigEntry) -> None:
        super().__init__(hub, entry, "setpoint")

    @property
    def native_min_value(self) -> float:
        value = self.coordinator.static_data.get("setpoint_min_pct")
        return value if value is not None else 0.0

    @property
    def native_max_value(self) -> float:
        value = self.coordinator.static_data.get("setpoint_max_pct")
        return value if value is not None else 100.0

    @property
    def native_value(self) -> float | None:
        return self._data_value("user_setpoint_pct")

    @property
    def available(self) -> bool:
        return super().available and self._data_value("user_setpoint_pct") is not None

    async def async_set_native_value(self, value: float) -> None:
        self._ensure_remote_control()
        # Register scale is 0.01 %, so 0-100 % maps to 0-10000.
        if not await self.coordinator.async_write_register(
            REG_SETPOINT, int(round(value * 100))
        ):
            self._raise_write_failed()


class Magna3MaxFlowLimit(Magna3Entity, NumberEntity):
    """Maximum flow limit FLOW in m³/h (register 00106, actual from 00345)."""

    _attr_translation_key = "max_flow_limit"
    _attr_icon = "mdi:water-alert-outline"
    _attr_native_unit_of_measurement = UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR
    _attr_native_min_value = 0.0
    _attr_native_max_value = 100.0
    _attr_native_step = 0.1
    _attr_mode = NumberMode.BOX

    def __init__(self, hub: Magna3Hub, entry: ConfigEntry) -> None:
        super().__init__(hub, entry, "max_flow_limit")

    @property
    def native_value(self) -> float | None:
        return self._data_value("max_flow_limit")

    @property
    def available(self) -> bool:
        return super().available and self._data_value("max_flow_limit") is not None

    async def async_set_native_value(self, value: float) -> None:
        self._ensure_remote_control()
        # Both register 00106 (write) and 00345 (readback) are scaled 0.01 m³/h.
        if not await self.coordinator.async_write_register(
            REG_MAX_FLOW_LIMIT, int(round(value * 100))
        ):
            self._raise_write_failed()
