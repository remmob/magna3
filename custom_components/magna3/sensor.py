"""Sensor platform for the Grundfos MAGNA3 integration."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, __version__ as HA_VERSION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .connection import HAS_SHARED_CONNECTION, active_method
from .const import DOMAIN, SENSOR_TYPES, Magna3SensorEntityDescription
from .entity import Magna3Entity
from .hub import Magna3Hub


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up MAGNA3 sensors."""
    hub: Magna3Hub = hass.data[DOMAIN][entry.entry_id]["hub"]
    entities: list[SensorEntity] = [
        Magna3Sensor(hub, entry, description) for description in SENSOR_TYPES.values()
    ]
    # TEMPORARY: shows which of the two connection methods this Home
    # Assistant instance uses. Remove once the 2026.9 migration is proven, or
    # fold into an attribute on an existing sensor.
    entities.append(Magna3ConnectionMethodSensor(hub, entry))
    async_add_entities(entities)


class Magna3Sensor(Magna3Entity, SensorEntity):
    """Sensor backed by a coordinator data key (values pre-scaled by the hub)."""

    entity_description: Magna3SensorEntityDescription

    def __init__(
        self,
        hub: Magna3Hub,
        entry: ConfigEntry,
        description: Magna3SensorEntityDescription,
    ) -> None:
        super().__init__(hub, entry, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        return self._data_value()

    @property
    def available(self) -> bool:
        return super().available and self._data_value() is not None


class Magna3ConnectionMethodSensor(Magna3Entity, SensorEntity):
    """TEMPORARY: shows which Modbus connection method is active.

    Reads no register — the value comes from connection.py and reflects only
    whether Home Assistant's `async_get_unit` was available (2026.9+, shared
    connection) or not (older, this integration opens its own socket). A
    diagnostic entity (EntityCategory.DIAGNOSTIC), so it appears at the
    bottom of the device rather than among the measurements.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:transit-connection-variant"
    _attr_translation_key = "connection_method"

    def __init__(self, hub: Magna3Hub, entry: ConfigEntry) -> None:
        super().__init__(hub, entry, "connection_method")

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> str:
        return active_method()

    @property
    def extra_state_attributes(self) -> dict:
        # Include the HA version so a screenshot shows at a glance why this
        # method was chosen.
        return {
            "shared_connection_available": HAS_SHARED_CONNECTION,
            "home_assistant_version": HA_VERSION,
        }
