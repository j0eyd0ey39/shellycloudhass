"""Platform for sensor integration."""
from __future__ import annotations

import logging
import aiohttp
import threading
import json

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from datetime import timedelta
from datetime import datetime

from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    DOMAIN,
 )

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=10)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    _LOGGER.info("async setup entry called, title:" + config_entry.title)
    """Set up the sensor platform."""
    cloudUpdater = ShellyCloudUpdater(config_entry.data["server"],config_entry.data["token"] )
    await cloudUpdater.async_updateAll()
    shellies = cloudUpdater.listShellyHTDevices()

    entities = []
    for shelly in shellies:
        entities.append(ShellyTempSensor(shelly, cloudUpdater))
        entities.append(ShellyHumiditySensor(shelly, cloudUpdater))
    
    async_add_entities(entities)
    _LOGGER.info("async setup entry finished, server:"+config_entry.data["server"]+" token:"+config_entry.data["token"])
    

class ShellyTempSensor(SensorEntity):
    """Representation of a Shelly Sensor."""
    def __init__(self, id, cloudUpdater) -> None:
        self._attr_cloudUpdater = cloudUpdater
        self._attr_device_id = id
        self._attr_name = "Shelly Temp "+id
        self._attr_native_value = cloudUpdater.getTemperature(self._attr_device_id)
        _LOGGER.info("shelly sensor created")

    
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    
    @property
    def unique_id(self) -> str | None:
        return self._attr_device_id+"tmp"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={                    
                (DOMAIN, self._attr_device_id)                
            },
            name="H&T "+self._attr_device_id,
            model="H&T",
            suggested_area="Kitchen",
            manufacturer="Shelly",
        )

    async def async_update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """        
        await self._attr_cloudUpdater.async_update()
        self._attr_native_value = self._attr_cloudUpdater.getTemperature(self._attr_device_id)
        _LOGGER.info("shelly sensor polled")

class ShellyHumiditySensor(SensorEntity):
    """Representation of a Shelly Sensor."""
    def __init__(self, id, cloudUpdater) -> None:
        self._attr_cloudUpdater = cloudUpdater
        self._attr_device_id = id
        self._attr_name = "Shelly Humidity "+id
        self._attr_native_value = cloudUpdater.getHumidity(id)
        _LOGGER.info("shelly sensor created")

    
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_state_class = SensorStateClass.MEASUREMENT
    
    @property
    def unique_id(self) -> str | None:
        return self._attr_device_id+"hum"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(            
            identifiers={                    
                (DOMAIN, self._attr_device_id)                
            },
            name="H&T "+self._attr_device_id,
            model="H&T",
            suggested_area="Kitchen",
            manufacturer="Shelly",            
        )

    async def async_update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """        
        await self._attr_cloudUpdater.async_update()
        self._attr_native_value = self._attr_cloudUpdater.getHumidity(self._attr_device_id)
        _LOGGER.info("shelly sensor polled")

class ShellyCloudUpdater:    
    def __init__(self, server, token) -> None:
        self._attr_lock = threading.RLock()
        self._attr_server = server
        self._attr_token = token
        self._attr_last_updated = datetime.now()-2*SCAN_INTERVAL

    async def async_update(self) -> None:
        """ Fetch shelly cloud info if scan interval has passed """
        with self._attr_lock:
          last_updated = self._attr_last_updated
          if datetime.now() - last_updated > SCAN_INTERVAL:
              _LOGGER.info("it is time to update")
              self._attr_last_updated = datetime.now()
              await self.async_updateAll()          

    async def async_updateAll(self) -> None:
        url = 'https://' + self._attr_server + '.shelly.cloud/device/all_status'        
        params = {"auth_key":self._attr_token}
        text = ""
        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=params) as resp:
                if not resp.status == 200:
                    _LOGGER.critical(resp)
                    return
                text = await resp.text()

        jsonData = json.loads(text)
        
        if jsonData["isok"] == True:
            data = jsonData["data"]
            with self._attr_lock:
              self._attr_devices_status = data["devices_status"]

    def getTemperature(self, id):
        with self._attr_lock:
          return self._attr_devices_status[id]["tmp"]["value"]
    
    def getHumidity(self, id):
        with self._attr_lock:
          return self._attr_devices_status[id]["hum"]["value"]
    
    def listShellyHTDevices(self):
        shellies = []
        with self._attr_lock:
          for key in self._attr_devices_status:
              if self._attr_devices_status[key]["getinfo"]["fw_info"]["device"].startswith("shellyht-"):
                  shellies.append(key)
        
        return shellies
 