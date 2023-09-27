"""Config flow for Shelly Cloud integration."""
from __future__ import annotations

import logging
import aiohttp

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from homeassistant.const import CONF_SCAN_INTERVAL

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, MIN_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class PlaceholderHub:
    def __init__(self, server: str) -> None:
        """Initialize."""
        self.server = server

    async def authenticate(self, token: str) -> bool:
        """Test if we can authenticate with the host."""
        url = "https://" + self.server + ".shelly.cloud/device/all_status"
        params = {"auth_key": token}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=params) as resp:
                if not resp.status == 200:
                    _LOGGER.critical(resp)
                    return False

        return True


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    hub = PlaceholderHub(data["server"])

    if not await hub.authenticate(data["token"]):
        raise InvalidAuth

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return info that you want to store in the config entry.
    return {
        "title": "Shelly Cloud Integration",
        "server": data["server"],
        "token": data["token"],
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Shelly Cloud."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        dataSchema = vol.Schema(
            {
                vol.Required(
                    "update_interval",
                    default=DEFAULT_SCAN_INTERVAL,
                ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=900)),
                vol.Required("server", default="shelly-32-eu"): str,
                vol.Required("token"): str,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=dataSchema, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
