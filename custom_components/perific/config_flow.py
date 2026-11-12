"""Config flow for Perific Energy Meter integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PerificAPI, PerificAuthError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required("token"): str,
    }
)


class PerificConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Perific Energy Meter integration."""

    VERSION = 1

    @callback
    def _async_step_schema(
        self, entry: ConfigEntry | None = None
    ) -> vol.Schema:
        """Return the account step schema, prefilled when reconfiguring."""
        if entry is not None:
            return STEP_USER_DATA_SCHEMA.extend(
                {
                    vol.Required(CONF_EMAIL, default=entry.data[CONF_EMAIL]): str,
                    vol.Required("token"): str,
                }
            )
        return STEP_USER_DATA_SCHEMA

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        return await self._async_step_account(user_input)

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> FlowResult:
        """Handle re-authentication after the API rejected the token."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask for a fresh token and validate it."""
        reauth_entry = self._get_reauth_entry()
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=self._async_step_schema(reauth_entry),
            )
        return await self._async_step_account(user_input, reauth_entry)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration (setting a new token)."""
        reconfigure_entry = self._get_reconfigure_entry()
        if user_input is None:
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=self._async_step_schema(reconfigure_entry),
            )
        return await self._async_step_account(user_input, reconfigure_entry)

    async def _async_step_account(
        self,
        user_input: dict[str, Any] | None,
        existing_entry: ConfigEntry | None = None,
    ) -> FlowResult:
        """Validate account data; create, reauth or reconfigure accordingly."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=self._async_step_schema(existing_entry),
            )

        errors = {}

        try:
            api = PerificAPI(
                user_input[CONF_EMAIL],
                user_input["token"],
                async_get_clientsession(self.hass),
            )

            # Check if user is activated
            if not await api.check_activation():
                errors["base"] = "invalid_auth"
                return self.async_show_form(
                    step_id=self.step_id,
                    data_schema=self._async_step_schema(existing_entry),
                    errors=errors,
                )

            # Refresh token to validate it
            await api.refresh_token()

            # Get user info to validate the connection
            user_info = await api.get_user_info()

            # Close the session
            await api.close()

        except PerificAuthError:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"

        if errors:
            return self.async_show_form(
                step_id=self.step_id,
                data_schema=self._async_step_schema(existing_entry),
                errors=errors,
            )

        if self.source == config_entries.SOURCE_REAUTH:
            target = self._get_reauth_entry()
            return self.async_update_reload_and_abort(
                target,
                data_updates=user_input,
            )

        if self.source == config_entries.SOURCE_RECONFIGURE:
            target = self._get_reconfigure_entry()
            return self.async_update_reload_and_abort(
                target,
                data_updates=user_input,
                reload_after_abort=False,
            )

        # Check if already configured
        await self.async_set_unique_id(user_info.get("Email"))
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"Perific ({user_info.get('Email')})",
            data=user_input,
        )


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""
