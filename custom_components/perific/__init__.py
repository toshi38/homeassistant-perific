"""The Perific Energy Meter integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PerificAPI, PerificAuthError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Perific from a config entry."""
    api = PerificAPI(
        entry.data[CONF_EMAIL],
        entry.data.get("token"),
        session=aiohttp_client.async_get_clientsession(hass),
    )

    try:
        if not await api.check_activation():
            raise ConfigEntryNotReady("User account is not activated")

        if entry.data.get("token"):
            await api.refresh_token()
    except PerificAuthError as err:
        raise ConfigEntryNotReady(f"Failed to authenticate: {err}") from err
    except Exception as err:
        raise ConfigEntryNotReady(f"Failed to initialize integration: {err}") from err

    coordinator = PerificDataUpdateCoordinator(hass, api)
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
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


class PerificDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Perific data."""

    def __init__(self, hass: HomeAssistant, api: PerificAPI) -> None:
        """Initialize."""
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            data: dict[str, Any] = {}

            user_info = await self.api.get_user_info()
            data["user"] = user_info

            items = await self.api.discover_items()
            data["items"] = {}

            for item in items:
                item_id = item["id"]
                data["items"][item_id] = {
                    "info": item,
                    "power": await self.api.get_current_power(item_id),
                    "energy_today": await self.api.get_energy_today(item_id),
                }

            return data
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err