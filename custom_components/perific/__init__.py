"""The Perific Energy Meter integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PerificAPI, PerificAuthError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Perific from a config entry."""
    api = PerificAPI(
        entry.data["email"],
        entry.data.get("token"),
        session=aiohttp_client.async_get_clientsession(hass),
    )

    def persist_token(token: str) -> None:
        """Keep the freshly obtained token in the config entry.

        Without this the entry keeps its original token forever; once that one
        expires (Enegic tokens are valid ~1 year) every later reload fails and
        a new app login is required.
        """
        if token and entry.data.get("token") != token:
            hass.config_entries.async_update_entry(
                entry, data={**entry.data, "token": token}
            )

    api.on_token_refreshed = persist_token

    try:
        # Check if user is activated and refresh token if needed
        if not await api.check_activation():
            raise ConfigEntryNotReady("User account is not activated")

        if api._token:
            await api.refresh_token()
    except PerificAuthError as err:
        # The stored token is dead (expired/revoked) - offer a reauth flow
        # so the user can enter a fresh one instead of retrying forever.
        raise ConfigEntryAuthFailed(f"Failed to authenticate: {err}") from err
    except Exception as err:
        raise ConfigEntryNotReady(f"Failed to authenticate: {err}") from err

    coordinator = PerificDataUpdateCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class PerificDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Perific data."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, api: PerificAPI
    ) -> None:
        """Initialize."""
        self.api = api
        self._entry = entry
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )
        self.api.on_token_refreshed = self._async_token_refreshed

    def _async_token_refreshed(self, token: str) -> None:
        """Store the freshly obtained token in the config entry."""
        if token and self._entry.data.get("token") != token:
            self.hass.config_entries.async_update_entry(
                self._entry,
                data={**self._entry.data, "token": token},
            )

    async def _async_update_data(self):
        """Fetch data from API."""
        try:
            data = {}

            # Get user info
            user_info = await self.api.get_user_info()
            data["user"] = user_info

            # Discover items/meters
            items = await self.api.discover_items()

            # Get power and energy data for each item
            data["items"] = {}
            for item in items:
                item_id = item["id"]
                item_data = {
                    "info": item,
                    "power": await self.api.get_current_power(item_id),
                    "energy_today": await self.api.get_energy_today(item_id),
                }

                data["items"][item_id] = item_data

            return data
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err
