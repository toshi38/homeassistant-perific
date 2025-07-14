"""Support for Perific energy meter sensors."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_FIRMWARE,
    ATTR_ITEM_ID,
    ATTR_ITEM_NAME,
    ATTR_SIGNAL_STRENGTH,
    ATTR_TIMESTAMP,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Perific sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []

    # Create sensors for each item
    for item_id, item_data in coordinator.data.get("items", {}).items():
        item_info = item_data["info"]
        item_name = item_info.get("name", f"Item {item_id}")

        # Power sensors
        entities.extend(
            [
                PerificPowerSensor(coordinator, item_id, item_name, "total"),
                PerificPowerSensor(coordinator, item_id, item_name, "l1"),
                PerificPowerSensor(coordinator, item_id, item_name, "l2"),
                PerificPowerSensor(coordinator, item_id, item_name, "l3"),
            ]
        )

        # Voltage sensors
        entities.extend(
            [
                PerificVoltageSensor(coordinator, item_id, item_name, "l1"),
                PerificVoltageSensor(coordinator, item_id, item_name, "l2"),
                PerificVoltageSensor(coordinator, item_id, item_name, "l3"),
            ]
        )

        # Current sensors
        entities.extend(
            [
                PerificCurrentSensor(coordinator, item_id, item_name, "l1"),
                PerificCurrentSensor(coordinator, item_id, item_name, "l2"),
                PerificCurrentSensor(coordinator, item_id, item_name, "l3"),
            ]
        )

        # Energy sensors
        entities.extend(
            [
                PerificEnergySensor(coordinator, item_id, item_name, "imported"),
                PerificEnergySensor(coordinator, item_id, item_name, "exported"),
                PerificEnergySensor(coordinator, item_id, item_name, "net"),
            ]
        )

    async_add_entities(entities)


class PerificSensorEntity(CoordinatorEntity, SensorEntity):
    """Base class for Perific sensor entities."""

    def __init__(
        self,
        coordinator,
        item_id: int,
        item_name: str,
        sensor_type: str,
        phase: str | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._item_id = item_id
        self._item_name = item_name
        self._sensor_type = sensor_type
        self._phase = phase

        # Build unique_id and entity_id
        if phase:
            self._attr_unique_id = f"{item_id}_{sensor_type}_{phase}"
            self._attr_name = f"{item_name} {sensor_type.title()} {phase.upper()}"
        else:
            self._attr_unique_id = f"{item_id}_{sensor_type}"
            self._attr_name = f"{item_name} {sensor_type.title()}"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        item_data = self.coordinator.data.get("items", {}).get(self._item_id, {})
        item_info = item_data.get("info", {})

        return {
            "identifiers": {(DOMAIN, self._item_id)},
            "name": self._item_name,
            "manufacturer": "Perific/Enegic",
            "model": item_info.get("subtype", "Energy Meter"),
            "sw_version": item_data.get("power", {}).get("firmware"),
            "via_device": (DOMAIN, "perific_hub"),
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        item_data = self.coordinator.data.get("items", {}).get(self._item_id, {})
        power_data = item_data.get("power", {})

        attrs = {
            ATTR_ITEM_ID: self._item_id,
            ATTR_ITEM_NAME: self._item_name,
        }

        if power_data.get("timestamp"):
            attrs[ATTR_TIMESTAMP] = power_data["timestamp"]
        if power_data.get("firmware"):
            attrs[ATTR_FIRMWARE] = power_data["firmware"]
        if power_data.get("signal_strength"):
            attrs[ATTR_SIGNAL_STRENGTH] = power_data["signal_strength"]

        return attrs


class PerificPowerSensor(PerificSensorEntity):
    """Representation of a Perific power sensor."""

    def __init__(self, coordinator, item_id: int, item_name: str, phase: str) -> None:
        """Initialize the power sensor."""
        super().__init__(coordinator, item_id, item_name, "power", phase)
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfPower.WATT

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        item_data = self.coordinator.data.get("items", {}).get(self._item_id, {})
        power_data = item_data.get("power", {})

        if power_data:
            power = power_data.get("power", {})
            if self._phase == "total":
                self._attr_native_value = power.get("total")
            else:
                self._attr_native_value = power.get(self._phase)
        else:
            self._attr_native_value = None

        super()._handle_coordinator_update()


class PerificVoltageSensor(PerificSensorEntity):
    """Representation of a Perific voltage sensor."""

    def __init__(self, coordinator, item_id: int, item_name: str, phase: str) -> None:
        """Initialize the voltage sensor."""
        super().__init__(coordinator, item_id, item_name, "voltage", phase)
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        item_data = self.coordinator.data.get("items", {}).get(self._item_id, {})
        power_data = item_data.get("power", {})

        if power_data:
            voltage = power_data.get("voltage", {})
            self._attr_native_value = voltage.get(self._phase)
        else:
            self._attr_native_value = None

        super()._handle_coordinator_update()


class PerificCurrentSensor(PerificSensorEntity):
    """Representation of a Perific current sensor."""

    def __init__(self, coordinator, item_id: int, item_name: str, phase: str) -> None:
        """Initialize the current sensor."""
        super().__init__(coordinator, item_id, item_name, "current", phase)
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        item_data = self.coordinator.data.get("items", {}).get(self._item_id, {})
        power_data = item_data.get("power", {})

        if power_data:
            current = power_data.get("current", {})
            self._attr_native_value = abs(
                current.get(self._phase, 0)
            )  # Use absolute value
        else:
            self._attr_native_value = None

        super()._handle_coordinator_update()


class PerificEnergySensor(PerificSensorEntity):
    """Representation of a Perific energy sensor."""

    def __init__(
        self, coordinator, item_id: int, item_name: str, energy_type: str
    ) -> None:
        """Initialize the energy sensor."""
        super().__init__(coordinator, item_id, item_name, f"energy_{energy_type}")
        self._energy_type = energy_type
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        item_data = self.coordinator.data.get("items", {}).get(self._item_id, {})

        if self._energy_type in ["imported", "exported", "net"]:
            energy_data = item_data.get("energy_today", {})
            self._attr_native_value = energy_data.get(self._energy_type, 0)
        else:
            # For total energy, use the imported/exported from power data
            power_data = item_data.get("power", {})
            if self._energy_type == "imported_total":
                self._attr_native_value = power_data.get("imported_energy", 0)
            elif self._energy_type == "exported_total":
                self._attr_native_value = power_data.get("exported_energy", 0)
            else:
                self._attr_native_value = None

        super()._handle_coordinator_update()
