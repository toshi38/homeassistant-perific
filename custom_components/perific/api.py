"""API client for Perific/Enegic energy meters (Corrected)."""

from __future__ import annotations

import logging
import ssl
from datetime import datetime, timedelta
from typing import Any

import aiohttp
import certifi
from aiohttp import ClientError, ClientSession

from .const import (
    API_ACCOUNT_OVERVIEW,
    API_BASE_URL,
    API_IS_ACTIVATED,
    API_ITEM_PARAMETERS,
    API_LATEST_PACKETS,
    API_PHASE_DATA,
    API_REFRESH_TOKEN,
    API_REPORTER_SETTINGS,
    API_USER_INFO,
    MAS_PER_AMPERE_HOUR,
    NOMINAL_VOLTAGE,
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

        # Create SSL context with proper certificates
        if session is None:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self._session = ClientSession(connector=connector)
            self._session_owner = True  # We created the session
        else:
            self._session = session
            self._session_owner = False  # Session provided by Home Assistant

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
                    self._token_expires = datetime.fromisoformat(
                        valid_to.replace("Z", "+00:00")
                    )

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
        if self._token_expires and datetime.now(self._token_expires.tzinfo) >= (
            self._token_expires - timedelta(minutes=5)
        ):
            await self.refresh_token()

    async def _request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Make an authenticated request."""
        await self._ensure_authenticated()

        headers = kwargs.pop("headers", {})
        headers.update(
            {
                "X-Authorization": self._token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

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
            async with self._session.post(
                url, data=form_data, headers=headers
            ) as response:
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

    @staticmethod
    def _phase_readings(data: dict[str, Any]) -> tuple[list[float], list[float], bool]:
        """Return (current, voltage, voltage_is_assumed) for one phase packet.

        Packet version 3 reports "hiavg" and "huavg", current and measured
        voltage. Packet version 2 clamp sensors report "iavg" only and carry no
        voltage register, so nominal voltage has to be assumed for those.
        """
        if data.get("hiavg"):
            current = list(data["hiavg"])[:3]
            voltage = list(data.get("huavg") or [])[:3]
            assumed = not data.get("huavg")
        else:
            current = list(data.get("iavg") or [])[:3]
            voltage = []
            assumed = True

        current = (current + [0.0, 0.0, 0.0])[:3]
        voltage = (voltage + [NOMINAL_VOLTAGE] * 3)[:3]
        return current, voltage, assumed

    @staticmethod
    def _cumulative_energy(latest_packets: dict[str, Any]) -> float | None:
        """Derive lifetime imported energy from the cumulative charge counters.

        Clamp sensors have no energy register. The "qmax" values are cumulative
        milliampere-seconds per phase, so energy is estimated at nominal
        voltage. Direction is not measured, so this is consumption only.
        """
        for packet_type in ("PhaseRealTime", "PhaseMinute", "PhaseHour", "PhaseDay"):
            data = latest_packets.get(packet_type, {}).get("data", {})
            qmax = data.get("qmax")
            if not qmax:
                continue
            ampere_hours = sum(qmax[:3]) / MAS_PER_AMPERE_HOUR
            return round(ampere_hours * NOMINAL_VOLTAGE / 1000.0, 3)
        return None

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

                        current, voltage, voltage_assumed = self._phase_readings(data)

                        # Calculate power per phase (P = U * I)
                        power_phases = [
                            abs(amps) * volts for amps, volts in zip(current, voltage)
                        ]
                        total_power = sum(power_phases)

                        return {
                            "timestamp": datetime.fromtimestamp(
                                phase_data.get("ts", 0) / 1000
                            ).isoformat(),
                            "power": {
                                "total": total_power,
                                "l1": power_phases[0],
                                "l2": power_phases[1],
                                "l3": power_phases[2],
                            },
                            "voltage": {
                                "l1": voltage[0],
                                "l2": voltage[1],
                                "l3": voltage[2],
                            },
                            "voltage_assumed": voltage_assumed,
                            "current": {
                                "l1": current[0],
                                "l2": current[1],
                                "l3": current[2],
                            },
                            "imported_energy": data.get("hwi", 0),
                            "exported_energy": data.get("hwo", 0),
                            "firmware": phase_data.get("fw"),
                            "signal_strength": phase_data.get("rssi"),
                        }

        return {}

    async def get_energy_today(self, item_id: int) -> dict[str, Any]:
        """Get energy totals for a meter."""
        packets = await self.get_latest_packets()

        for packet in packets:
            if packet.get("ItemId") != item_id:
                continue

            latest_packets = packet.get("LatestPackets", {})
            day_data = latest_packets.get("PhaseDay", {}).get("data", {})

            if "hwpi" in day_data or "hwpo" in day_data:
                imported_today = sum(day_data.get("hwpi", [0, 0, 0]))
                exported_today = sum(day_data.get("hwpo", [0, 0, 0]))

                return {
                    "imported": imported_today,
                    "exported": exported_today,
                    "net": imported_today - exported_today,
                    "unit": "kWh",
                }

            # Clamp sensors have no energy register. Fall back to the
            # cumulative charge counters. They only measure magnitude, so
            # export and net stay unknown rather than being reported as zero.
            cumulative = self._cumulative_energy(latest_packets)
            if cumulative is not None:
                return {
                    "imported": cumulative,
                    "exported": None,
                    "net": None,
                    "unit": "kWh",
                    "source": "charge_counters",
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

                    items.append(
                        {
                            "id": item_id,
                            "name": actual_params.get("Name", f"Item {item_id}"),
                            "system_name": actual_params.get("SystemName", ""),
                            "type": actual_params.get("ItemType", "Phase"),
                            "subtype": actual_params.get("ItemSubType", ""),
                            "category": actual_params.get("ItemCategory", ""),
                            "mac": actual_params.get("Mac", ""),
                            "timezone": actual_params.get("TimeZone", ""),
                        }
                    )
                except Exception as e:
                    _LOGGER.warning(f"Could not get parameters for item {item_id}: {e}")
                    items.append(
                        {
                            "id": item_id,
                            "name": f"Item {item_id}",
                            "system_name": "",
                            "type": "Phase",
                            "subtype": "",
                            "category": "",
                            "mac": "",
                            "timezone": "",
                        }
                    )

        self._items = items
        return items

    async def close(self) -> None:
        """Close the session."""
        # Only close the session if we created it
        if self._session_owner:
            await self._session.close()
