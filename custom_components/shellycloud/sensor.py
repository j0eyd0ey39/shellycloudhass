"""Platform for sensor integration."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature, PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from homeassistant.helpers.device_registry import (
    async_get as dr_async_get,
)

from . import coordinator

from .const import (
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    _LOGGER.info("async setup entry called, title:" + config_entry.title)
    # Set up the sensor platform.

    cloudCoordinator = coordinator.ShellyCloudCoordinator(
        hass,
        config_entry.data["server"],
        config_entry.data["token"],
        config_entry.data["update_interval"],
    )
    await cloudCoordinator.async_config_entry_first_refresh()
    shellies = cloudCoordinator.listShellyHTDevices()

    entities = []
    for shelly in shellies:
        entities.append(ShellyTempSensor(shelly, cloudCoordinator, hass))
        entities.append(ShellyHumiditySensor(shelly, cloudCoordinator, hass))

    async_add_entities(entities)

    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = cloudCoordinator
    _LOGGER.debug(
        "async setup entry finished, server:"
        + config_entry.data["server"]
        + " token:"
        + config_entry.data["token"]
        + " update interval:"
        + str(config_entry.data["update_interval"])
    )


class ShellyBaseDevice(CoordinatorEntity):
    """Representation of a Shelly Device"""

    def __init__(
        self, shellyId, deviceModelName, cloudCoordinator, hass: HomeAssistant
    ) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(cloudCoordinator, context=shellyId)
        self._attr_device_id = shellyId
        self._attr_hass = hass
        self._attr_device_model = deviceModelName
        self._attr_sw_version = self.coordinator.data[self._attr_device_id]["getinfo"][
            "fw_info"
        ]["fw"]

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._attr_device_id)},
            name=self._attr_device_model + " " + self._attr_device_id,
            model=self._attr_device_model,
            suggested_area="Kitchen",
            manufacturer="Shelly",
            sw_version=self._attr_sw_version,
        )


class ShellyHTDevice(ShellyBaseDevice):
    """Representation of a Shelly H&T Device"""

    def __init__(self, shellyId, cloudCoordinator, hass: HomeAssistant) -> None:
        """Pass coordinator to Shelly base device"""
        super().__init__(shellyId, "H&T", cloudCoordinator, hass)

    def checkVersion(self) -> None:
        sw_version = self.coordinator.data[self._attr_device_id]["getinfo"]["fw_info"][
            "fw"
        ]
        if self._attr_sw_version != sw_version:
            dev_reg = dr_async_get(self._attr_hass)
            if device := dev_reg.async_get_device(
                identifiers={(DOMAIN, self._attr_device_id)},
            ):
                dev_reg.async_update_device(device.id, sw_version=sw_version)
                self._attr_sw_version = sw_version


class ShellyHumiditySensor(SensorEntity, ShellyHTDevice):
    """Representation of a Shelly Sensor."""

    def __init__(self, shellyId, cloudCoordinator, hass: HomeAssistant) -> None:
        """Pass coordinator to parent."""
        super().__init__(shellyId, cloudCoordinator, hass)
        self._attr_device_id = shellyId
        self._attr_name = "Shelly Humidity " + shellyId
        self._attr_native_value = self.coordinator.data[self._attr_device_id]["hum"][
            "value"
        ]
        _LOGGER.debug("Shelly humidity sensor created")

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str | None:
        return self._attr_device_id + "hum"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.coordinator.data[self._attr_device_id]["hum"][
            "value"
        ]
        _LOGGER.debug("Shelly humidity sensor polled")
        self.checkVersion()
        self.async_write_ha_state()


class ShellyTempSensor(SensorEntity, ShellyHTDevice):
    """Representation of a Shelly Sensor."""

    def __init__(self, shellyId, coordinator, hass: HomeAssistant) -> None:
        """Pass coordinator to parent."""
        super().__init__(shellyId, coordinator, hass)
        self._attr_device_id = shellyId
        self._attr_name = "Shelly Temp " + shellyId
        self._attr_native_value = self.coordinator.data[self._attr_device_id]["tmp"][
            "value"
        ]
        _LOGGER.debug("Shelly temperature sensor created")

    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str | None:
        return self._attr_device_id + "tmp"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.coordinator.data[self._attr_device_id]["tmp"][
            "value"
        ]
        _LOGGER.debug("Shelly temp sensor polled")
        self.checkVersion()
        self.async_write_ha_state()
