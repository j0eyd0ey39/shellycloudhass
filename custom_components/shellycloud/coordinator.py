from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)
from homeassistant.core import HomeAssistant
from datetime import timedelta
import aiohttp
import json
import async_timeout
import logging

_LOGGER = logging.getLogger(__name__)


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
