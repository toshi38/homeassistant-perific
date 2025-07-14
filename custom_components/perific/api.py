"""API client for Perific/Enegic energy meters (Corrected)."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from aiohttp import ClientError, ClientSession

from .const import (
    API_BASE_URL,
    API_IS_ACTIVATED,
    API_REFRESH_TOKEN,
    API_USER_INFO,
    API_ACCOUNT_OVERVIEW,
    API_LATEST_PACKETS,
    API_PHASE_DATA,
    API_ITEM_PARAMETERS,
    API_REPORTER_SETTINGS,
)

_LOGGER = logging.getLogger(__name__)


class PerificAuthError(Exception):
    """Authentication error."""


class PerificAPIError(Exception):
    """API error."""


class PerificAPI:
    """API client for Perific/Enegic."""

    def __init__(
        self,
        username: str,
        token: str | None = None,
        session: ClientSession | None = None,
    ) -> None:
        """Initialize the API client."""
        self._username = username
        self._token = token
        self._session = session or ClientSession()
        self._token_expires: datetime | None = None
        self._user_id: int | None = None
        self._items: list[dict[str, Any]] = []

    async def check_activation(self) -> bool:
        """Check if user is activated."""
        data = {"username": self._username}
        
        try:
            async with self._session.put(
                f"{API_BASE_URL}{API_IS_ACTIVATED}",
                json=data,
                headers={"Content-Type": "application/json"},
            ) as response:
                response.raise_for_status()
                result = await response.json()
                return result.get("UserIsActivated", False)
        except ClientError as err:
            raise PerificAuthError(f"Activation check failed: {err}") from err

    async def refresh_token(self) -> None:
        """Refresh the access token."""
        if not self._token:
            raise PerificAuthError("No token to refresh")
            
        data = {"token": self._token}
        
        try:
            async with self._session.put(
                f"{API_BASE_URL}{API_REFRESH_TOKEN}",
                json=data,
                headers={
                    "Content-Type": "application/json",
                    "X-Authorization": self._token,
                },
            ) as response:
                response.raise_for_status()
                result = await response.json()
                
                token_info = result.get("TokenInfo", {})
                self._token = token_info.get("Token")
                
                # Parse expiration
                valid_to = token_info.get("ValidTo")
                if valid_to:
                    self._token_expires = datetime.fromisoformat(valid_to.replace("Z", "+00:00"))
                
                # Store user ID
                user_info = result.get("User", {})
                self._user_id = user_info.get("UserId")
                
        except ClientError as err:
            raise PerificAuthError(f"Token refresh failed: {err}") from err

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid token."""
        if not self._token:
            raise PerificAuthError("No token available")
        
        # Check if token is expired (with 5 minute buffer)
        if self._token_expires and datetime.now(self._token_expires.tzinfo) >= (self._token_expires - timedelta(minutes=5)):
            await self.refresh_token()

    async def _request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Make an authenticated request."""
        await self._ensure_authenticated()
        
        headers = kwargs.pop("headers", {})
        headers.update({
            "X-Authorization": self._token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        
        url = f"{API_BASE_URL}{endpoint}"
        
        try:
            async with self._session.request(
                method, url, headers=headers, **kwargs
            ) as response:
                response.raise_for_status()
                return await response.json()
        except ClientError as err:
            raise PerificAPIError(f"API request failed: {err}") from err

    async def get_user_info(self) -> dict[str, Any]:
        """Get user information."""
        return await self._request("GET", API_USER_INFO)

    async def get_account_overview(self) -> dict[str, Any]:
        """Get account overview including items."""
        data = {"IncludeSharedItems": True}
        return await self._request("POST", API_ACCOUNT_OVERVIEW, json=data)

    async def get_latest_packets(self) -> list[dict[str, Any]]:
        """Get latest meter readings."""
        return await self._request("PUT", API_LATEST_PACKETS)

    async def get_phase_data(
        self,
        item_id: int,
        from_date: datetime,
        to_date: datetime,
        data_type: str = "Avg",
    ) -> list[dict[str, Any]]:
        """Get phase data for time range."""
        # This endpoint uses form data
        form_data = aiohttp.FormData()
        form_data.add_field("itemId", str(item_id))
        form_data.add_field("fromDate", from_date.isoformat())
        form_data.add_field("toDate", to_date.isoformat())
        form_data.add_field("dataType", data_type)
        
        headers = {"X-Authorization": self._token}
        
        url = f"{API_BASE_URL}{API_PHASE_DATA}"
        
        try:
            async with self._session.post(url, data=form_data, headers=headers) as response:
                response.raise_for_status()
                return await response.json()
        except ClientError as err:
            raise PerificAPIError(f"Phase data request failed: {err}") from err

    async def get_item_parameters(self, item_id: int) -> dict[str, Any]:
        """Get item parameters."""
        data = {"itemId": item_id}
        return await self._request("PUT", API_ITEM_PARAMETERS, json=data)

    async def get_reporter_settings(self) -> dict[str, Any]:
        """Get reporter settings (EV chargers, etc.)."""
        return await self._request("POST", API_REPORTER_SETTINGS)


    async def get_current_power(self, item_id: int) -> dict[str, Any]:
        """Get current power reading from latest packets."""
        packets = await self.get_latest_packets()
        
        for packet in packets:
            if packet.get("ItemId") == item_id:
                latest_packets = packet.get("LatestPackets", {})
                
                # Try to get the most recent data
                for packet_type in ["PhaseRealTime", "PhaseMinute", "PhaseHour"]:
                    if packet_type in latest_packets:
                        phase_data = latest_packets[packet_type]
                        data = phase_data.get("data", {})
                        
                        # Calculate total power from current and voltage
                        hiavg = data.get("hiavg", [0, 0, 0])
                        huavg = data.get("huavg", [230, 230, 230])
                        
                        # Calculate power per phase (P = U * I)
                        power_phases = [abs(current) * voltage for current, voltage in zip(hiavg, huavg)]
                        total_power = sum(power_phases)
                        
                        return {
                            "timestamp": datetime.fromtimestamp(phase_data.get("ts", 0) / 1000).isoformat(),
                            "power": {
                                "total": total_power,
                                "l1": power_phases[0],
                                "l2": power_phases[1],
                                "l3": power_phases[2],
                            },
                            "voltage": {
                                "l1": huavg[0],
                                "l2": huavg[1],
                                "l3": huavg[2],
                            },
                            "current": {
                                "l1": hiavg[0],
                                "l2": hiavg[1],
                                "l3": hiavg[2],
                            },
                            "imported_energy": data.get("hwi", 0),
                            "exported_energy": data.get("hwo", 0),
                            "firmware": phase_data.get("fw"),
                            "signal_strength": phase_data.get("rssi"),
                        }
        
        return {}

    async def get_energy_today(self, item_id: int) -> dict[str, Any]:
        """Get today's energy consumption."""
        packets = await self.get_latest_packets()
        
        for packet in packets:
            if packet.get("ItemId") == item_id:
                latest_packets = packet.get("LatestPackets", {})
                
                # Get day data if available
                if "PhaseDay" in latest_packets:
                    day_data = latest_packets["PhaseDay"].get("data", {})
                    
                    # Calculate energy from power data
                    hwpi = day_data.get("hwpi", [0, 0, 0])
                    hwpo = day_data.get("hwpo", [0, 0, 0])
                    
                    imported_today = sum(hwpi)
                    exported_today = sum(hwpo)
                    
                    return {
                        "imported": imported_today,
                        "exported": exported_today,
                        "net": imported_today - exported_today,
                        "unit": "kWh",
                    }
        
        return {"imported": 0, "exported": 0, "net": 0, "unit": "kWh"}

    async def discover_items(self) -> list[dict[str, Any]]:
        """Discover available items/meters."""
        packets = await self.get_latest_packets()
        items = []
        
        for packet in packets:
            item_id = packet.get("ItemId")
            if item_id:
                # Get item parameters for more details
                try:
                    params = await self.get_item_parameters(item_id)
                    actual_params = params.get("ActualParameters", {})
                    
                    items.append({
                        "id": item_id,
                        "name": actual_params.get("Name", f"Item {item_id}"),
                        "system_name": actual_params.get("SystemName", ""),
                        "type": actual_params.get("ItemType", "Phase"),
                        "subtype": actual_params.get("ItemSubType", ""),
                        "category": actual_params.get("ItemCategory", ""),
                        "mac": actual_params.get("Mac", ""),
                        "timezone": actual_params.get("TimeZone", ""),
                    })
                except Exception as e:
                    _LOGGER.warning(f"Could not get parameters for item {item_id}: {e}")
                    items.append({
                        "id": item_id,
                        "name": f"Item {item_id}",
                        "system_name": "",
                        "type": "Phase",
                        "subtype": "",
                        "category": "",
                        "mac": "",
                        "timezone": "",
                    })
        
        self._items = items
        return items

    async def close(self) -> None:
        """Close the session."""
        await self._session.close()