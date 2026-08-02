"""Binary sensor platform for the Grundfos MAGNA3 integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BINARY_SENSOR_TYPES, DOMAIN
from .entity import Magna3Entity
from .hub import Magna3Hub

CONNECTIVITY_DESCRIPTION = BinarySensorEntityDescription(
    key="connectivity",
    translation_key="connectivity",
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up MAGNA3 binary sensors."""
    hub: Magna3Hub = hass.data[DOMAIN][entry.entry_id]["hub"]
    entities: list[BinarySensorEntity] = [
        Magna3StatusBitSensor(hub, entry, description)
        for description in BINARY_SENSOR_TYPES
    ]
    entities.append(Magna3ConnectivitySensor(hub, entry))
    async_add_entities(entities)


class Magna3StatusBitSensor(Magna3Entity, BinarySensorEntity):
    """Binary sensor backed by a StatusBits bit."""

    def __init__(
        self,
        hub: Magna3Hub,
        entry: ConfigEntry,
        description: BinarySensorEntityDescription,
    ) -> None:
        super().__init__(hub, entry, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        value = self._data_value()
        return None if value is None else bool(value)

    @property
    def available(self) -> bool:
        return super().available and self._data_value() is not None


class Magna3ConnectivitySensor(Magna3Entity, BinarySensorEntity):
    """Reports whether Modbus communication with the pump is healthy."""

    def __init__(self, hub: Magna3Hub, entry: ConfigEntry) -> None:
        super().__init__(hub, entry, CONNECTIVITY_DESCRIPTION.key)
        self.entity_description = CONNECTIVITY_DESCRIPTION

    @property
    def is_on(self) -> bool:
        return self._data_value("connection_status") == "OK"

    @property
    def available(self) -> bool:
        # Stays available to be able to report a lost connection.
        return True
