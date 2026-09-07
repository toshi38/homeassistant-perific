"""API client for Perific/Enegic energy meters."""

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
        self._token_expires: datetime | None = None
        self._user_id: int | None = None
        self._items: list[dict[str, Any]] = []

        if session is None:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self._session = ClientSession(connector=connector)
            self._session_owner = True
        else:
            self._session = session
            self._session_owner = False

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
                    "Accept": "application/json",
                },
            ) as response:
                response.raise_for_status()
                result = await response.json()

                token_info = result.get("TokenInfo", {})
                new_token = token_info.get("Token") or result.get("token")
                if new_token:
                    self._token = new_token

                valid_to = token_info.get("ValidTo")
                if valid_to:
                    self._token_expires = datetime.fromisoformat(
                        valid_to.replace("Z", "+00:00")
                    )

                user_info = result.get("User", {})
                self._user_id = user_info.get("UserId")
        except ClientError as err:
            raise PerificAuthError(f"Token refresh failed: {err}") from err

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid token."""
        if not self._token:
            raise PerificAuthError("No token available")

        if self._token_expires and datetime.now(self._token_expires.tzinfo) >= (
            self._token_expires - timedelta(minutes=5)
        ):
            await self.refresh_token()

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json: dict[str, Any] | None = None,
        data: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        """Make an authenticated request."""
        await self._ensure_authenticated()

        request_headers = {
            "X-Authorization": self._token,
            "Accept": "application/json",
        }
        if headers:
            request_headers.update(headers)

        if json is not None:
            request_headers.setdefault("Content-Type", "application/json")

        url = f"{API_BASE_URL}{endpoint}"

        try:
            async with self._session.request(
                method,
                url,
                headers=request_headers,
                json=json,
                data=data,
            ) as response:
                text = await response.text()

                _LOGGER.debug(
                    "Perific API %s %s -> %s, json=%s, response=%s",
                    method,
                    url,
                    response.status,
                    json,
                    text[:2000],
                )

                response.raise_for_status()

                if not text.strip():
                    return []

                return await response.json()
        except ClientError as err:
            raise PerificAPIError(f"API request failed: {err}") from err

    async def get_user_info(self) -> dict[str, Any]:
        """Get user information."""
        result = await self._request("GET", API_USER_INFO)
        return result if isinstance(result, dict) else {}

    async def get_account_overview(self) -> dict[str, Any]:
        """Get account overview including items."""
        result = await self._request(
            "GET",
            API_ACCOUNT_OVERVIEW,
            json={"IncludeSharedItems": True},
        )
        return result if isinstance(result, dict) else {}

    async def get_latest_packets(self) -> list[dict[str, Any]]:
        """Get latest meter readings."""
        result = await self._request(
            "PUT",
            API_LATEST_PACKETS,
            json={"IncludeSharedItems": True},
        )
        return result if isinstance(result, list) else []

    async def get_phase_data(
        self,
        item_id: int,
        from_date: datetime,
        to_date: datetime,
        data_type: str = "Avg",
    ) -> list[dict[str, Any]]:
        """Get phase data for time range."""
        form_data = aiohttp.FormData()
        form_data.add_field("itemId", str(item_id))
        form_data.add_field("fromDate", from_date.isoformat())
        form_data.add_field("toDate", to_date.isoformat())
        form_data.add_field("dataType", data_type)

        result = await self._request(
            "POST",
            API_PHASE_DATA,
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        return result if isinstance(result, list) else []

    async def get_item_parameters(self, item_id: int) -> dict[str, Any]:
        """Get item parameters."""
        result = await self._request(
            "PUT",
            API_ITEM_PARAMETERS,
            json={"itemId": item_id},
        )
        return result if isinstance(result, dict) else {}

    async def get_reporter_settings(self) -> dict[str, Any]:
        """Get reporter settings."""
        result = await self._request("POST", API_REPORTER_SETTINGS)
        return result if isinstance(result, dict) else {}

    async def get_current_power(self, item_id: int) -> dict[str, Any]:
        """Get current power reading from latest packets."""
        packets = await self.get_latest_packets()

        for packet in packets:
            packet_item_id = (
                packet.get("ItemId")
                or packet.get("itemId")
                or packet.get("iid")
                or packet.get("item_id")
            )

            if packet_item_id is None or str(packet_item_id) != str(item_id):
                continue

            latest_packets = packet.get("LatestPackets", {}) or {}

            for packet_type in ("PhaseRealTime", "PhaseMinute", "PhaseHour", "PhaseDay"):
                phase_packet = latest_packets.get(packet_type)
                if not phase_packet:
                    continue

                data = phase_packet.get("data", {}) or {}
                hiavg = data.get("hiavg") or data.get("iavg")
                huavg = data.get("huavg")

                if not isinstance(hiavg, list) or len(hiavg) < 3:
                    continue

                if not isinstance(huavg, list) or len(huavg) < 3:
                    huavg = [230.0, 230.0, 230.0]

                try:
                    currents = [float(x) for x in hiavg[:3]]
                    voltages = [float(x) for x in huavg[:3]]
                except (TypeError, ValueError):
                    continue

                power_phases = [abs(i) * v for i, v in zip(currents, voltages)]

                ts = phase_packet.get("ts")
                timestamp = None
                if ts:
                    try:
                        timestamp = datetime.fromtimestamp(ts / 1000).isoformat()
                    except (TypeError, ValueError, OSError):
                        timestamp = None

                return {
                    "timestamp": timestamp,
                    "power": {
                        "total": sum(power_phases),
                        "l1": power_phases[0],
                        "l2": power_phases[1],
                        "l3": power_phases[2],
                    },
                    "voltage": {
                        "l1": voltages[0],
                        "l2": voltages[1],
                        "l3": voltages[2],
                    },
                    "current": {
                        "l1": currents[0],
                        "l2": currents[1],
                        "l3": currents[2],
                    },
                    "imported_energy": data.get("hwi"),
                    "exported_energy": data.get("hwo"),
                    "firmware": phase_packet.get("fw"),
                    "signal_strength": phase_packet.get("rssi"),
                    "packet_type": packet_type,
                }

        return {}

    async def get_energy_today(self, item_id: int) -> dict[str, Any]:
        """Get today's energy values."""
        packets = await self.get_latest_packets()

        for packet in packets:
            packet_item_id = (
                packet.get("ItemId")
                or packet.get("itemId")
                or packet.get("iid")
                or packet.get("item_id")
            )

            if packet_item_id is None or str(packet_item_id) != str(item_id):
                continue

            latest_packets = packet.get("LatestPackets", {}) or {}

            for packet_type in ("PhaseDay", "PhaseHour"):
                phase_packet = latest_packets.get(packet_type)
                if not phase_packet:
                    continue

                data = phase_packet.get("data", {}) or {}

                hwpi = data.get("hwpi")
                hwpo = data.get("hwpo")
                hwi = data.get("hwi")
                hwo = data.get("hwo")

                if hwpi is None and hwpo is None and hwi is None and hwo is None:
                    continue

                imported = 0.0
                exported = 0.0

                if isinstance(hwpi, list):
                    imported = sum(float(x) for x in hwpi[:3] if x is not None)
                elif hwpi is not None:
                    imported = float(hwpi)
                elif hwi is not None:
                    imported = float(hwi)

                if isinstance(hwpo, list):
                    exported = sum(float(x) for x in hwpo[:3] if x is not None)
                elif hwpo is not None:
                    exported = float(hwpo)
                elif hwo is not None:
                    exported = float(hwo)

                return {
                    "imported": imported,
                    "exported": exported,
                    "net": imported - exported,
                    "unit": "kWh",
                    "packet_type": packet_type,
                }

        return {
            "imported": None,
            "exported": None,
            "net": None,
            "unit": "kWh",
        }

    async def discover_items(self) -> list[dict[str, Any]]:
        """Discover available items/meters."""
        packets = await self.get_latest_packets()
        items: list[dict[str, Any]] = []

        for packet in packets:
            item_id = (
                packet.get("ItemId")
                or packet.get("itemId")
                or packet.get("iid")
                or packet.get("item_id")
            )

            if not item_id:
                continue

            try:
                params = await self.get_item_parameters(int(item_id))
                actual_params = params.get("ActualParameters", {})

                items.append(
                    {
                        "id": int(item_id),
                        "name": actual_params.get("Name", f"Item {item_id}"),
                        "system_name": actual_params.get("SystemName", ""),
                        "type": actual_params.get("ItemType", "Phase"),
                        "subtype": actual_params.get("ItemSubType", ""),
                        "category": actual_params.get("ItemCategory", ""),
                        "mac": actual_params.get("Mac", ""),
                        "timezone": actual_params.get("TimeZone", ""),
                    }
                )
            except Exception as err:
                _LOGGER.warning("Could not get parameters for item %s: %s", item_id, err)
                items.append(
                    {
                        "id": int(item_id),
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
        if self._session_owner:
            await self._session.close()