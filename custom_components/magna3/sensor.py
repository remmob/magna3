"""Sensor platform for the Grundfos MAGNA3 integration."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SENSOR_TYPES, Magna3SensorEntityDescription
from .entity import Magna3Entity
from .hub import Magna3Hub


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up MAGNA3 sensors."""
    hub: Magna3Hub = hass.data[DOMAIN][entry.entry_id]["hub"]
    async_add_entities(
        Magna3Sensor(hub, entry, description) for description in SENSOR_TYPES.values()
    )


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
