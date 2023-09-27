"""Platform for sensor integration."""
from __future__ import annotations

import logging
import aiohttp
import threading
import json

import async_timeout

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature, PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from datetime import timedelta

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

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

    coordinator = ShellyCloudCoordinator(
        hass,
        config_entry.data["server"],
        config_entry.data["token"],
        config_entry.data["update_interval"],
    )
    await coordinator.async_config_entry_first_refresh()
    shellies = coordinator.listShellyHTDevices()

    entities = []
    for shelly in shellies:
        entities.append(ShellyTempSensor(shelly, coordinator))
        entities.append(ShellyHumiditySensor(shelly, coordinator))

    async_add_entities(entities)
    _LOGGER.debug(
        "async setup entry finished, server:"
        + config_entry.data["server"]
        + " token:"
        + config_entry.data["token"]
        + " update interval:"
        + str(config_entry.data["update_interval"])
    )


class ShellyTempSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Shelly Sensor."""

    def __init__(self, shellyId, coordinator) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, context=shellyId)
        self._attr_device_id = shellyId
        self._attr_name = "Shelly Temp " + shellyId
        _LOGGER.debug("Shelly sensor created")

    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str | None:
        return self._attr_device_id + "tmp"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._attr_device_id)},
            name="H&T " + self._attr_device_id,
            model="H&T",
            suggested_area="Kitchen",
            manufacturer="Shelly",
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.coordinator.data[self._attr_device_id]["tmp"][
            "value"
        ]
        _LOGGER.debug("Shelly sensor polled")
        self.async_write_ha_state()


class ShellyHumiditySensor(CoordinatorEntity, SensorEntity):
    """Representation of a Shelly Sensor."""

    def __init__(self, shellyId, coordinator) -> None:
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator, context=shellyId)
        self._attr_device_id = shellyId
        self._attr_name = "Shelly Humidity " + shellyId
        _LOGGER.debug("Shelly sensor created")

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def unique_id(self) -> str | None:
        return self._attr_device_id + "hum"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._attr_device_id)},
            name="H&T " + self._attr_device_id,
            model="H&T",
            suggested_area="Kitchen",
            manufacturer="Shelly",
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.coordinator.data[self._attr_device_id]["hum"][
            "value"
        ]
        _LOGGER.debug("Shelly sensor polled")
        self.async_write_ha_state()


class ShellyCloudCoordinator(DataUpdateCoordinator):
    """Shelly cloud custom coordinator."""

    def __init__(self, hass: HomeAssistant, server, token, update_interval) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="ShellyCloudCoordinator",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=update_interval),
        )
        self._attr_server = server
        self._attr_token = token

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        # Note: asyncio.TimeoutError and aiohttp.ClientError are already
        # handled by the data update coordinator.
        async with async_timeout.timeout(10):
            url = "https://" + self._attr_server + ".shelly.cloud/device/all_status"
            params = {"auth_key": self._attr_token}
            text = ""
            async with aiohttp.ClientSession() as session:
                async with session.post(url, params=params) as resp:
                    if not resp.status == 200:
                        _LOGGER.critical(resp)
                        return
                    text = await resp.text()

            jsonData = json.loads(text)
            if jsonData["isok"] == True:
                return jsonData["data"]["devices_status"]

    def listShellyHTDevices(self):
        shellies = []
        for key in self.data:
            if self.data[key]["getinfo"]["fw_info"]["device"].startswith("shellyht-"):
                shellies.append(key)

        return shellies
