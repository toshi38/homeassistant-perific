"""Config flow for Perific Energy Meter integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PerificAPI, PerificAuthError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_TOKEN = "token"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_TOKEN): str,
    }
)


class PerificConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Perific Energy Meter."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
            )

        errors: dict[str, str] = {}

        try:
            api = PerificAPI(
                user_input[CONF_EMAIL],
                user_input[CONF_TOKEN],
                async_get_clientsession(self.hass),
            )

            if not await api.check_activation():
                errors["base"] = "invalid_auth"
                return self.async_show_form(
                    step_id="user",
                    data_schema=STEP_USER_DATA_SCHEMA,
                    errors=errors,
                )

            await api.refresh_token()
            user_info = await api.get_user_info()

        except PerificAuthError:
            errors["base"] = "invalid_auth"
        except Exception:
            _LOGGER.exception("Unexpected exception during config flow")
            errors["base"] = "unknown"
        else:
            unique_id = (
                str(user_info.get("Email"))
                or str(user_input[CONF_EMAIL]).lower()
            )
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"Perific ({user_info.get('Email', user_input[CONF_EMAIL])})",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )