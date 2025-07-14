#!/usr/bin/env python3
"""Standalone test script for Perific API."""
import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import aiohttp

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")
    print("   You can also set environment variables manually.")

# Import mock data
from mock_data import MOCK_LATEST_PACKETS, get_mock_response


class PerificAPI:
    """Simplified API client for testing."""

    def __init__(self, username: str, token: str):
        self._username = username
        self._token = token
        self._session = None

    async def __aenter__(self):
        # Skip SSL verification for testing
        connector = aiohttp.TCPConnector(ssl=False)
        self._session = aiohttp.ClientSession(connector=connector)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()

    async def _request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Make an authenticated request."""
        headers = kwargs.pop("headers", {})
        headers.update(
            {
                "X-Authorization": self._token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

        url = f"https://api.enegic.com{endpoint}"

        async with self._session.request(
            method, url, headers=headers, **kwargs
        ) as response:
            response.raise_for_status()
            return await response.json()

    async def get_user_info(self) -> dict[str, Any]:
        """Get user information."""
        return await self._request("GET", "/getuserinfo")

    async def get_latest_packets(self) -> list[dict[str, Any]]:
        """Get latest meter readings."""
        return await self._request("PUT", "/getlatestpackets")

    async def get_item_parameters(self, item_id: int) -> dict[str, Any]:
        """Get item parameters."""
        data = {"itemId": item_id}
        return await self._request("PUT", "/getitemuserparameters", json=data)


async def mock_aiohttp_request(url, method="GET", **kwargs):
    """Mock aiohttp request for testing."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=get_mock_response(url, method))
    mock_response.raise_for_status = AsyncMock()
    return mock_response


async def test_api():
    """Test the Perific API."""
    # Check if running in CI mode
    use_mocks = os.getenv("CI") == "true"

    # Load credentials from environment variables or .env file
    email = os.getenv("PERIFIC_EMAIL", "test@example.com")
    token = os.getenv("PERIFIC_TOKEN", "mock-token-12345")

    if not use_mocks and (not email or not token):
        print("❌ Missing credentials!")
        print("   Set environment variables: PERIFIC_EMAIL and PERIFIC_TOKEN")
        print("   Or create a .env file with your credentials")
        print("   See .env.example for format")
        return

    # Set up mocking if in CI mode
    if use_mocks:
        print("🔧 Testing Perific API with mocked responses...")
        print(f"📧 Email: {email}")
        print(f"🔑 Token: {token[:20]}...")

        # Mock aiohttp session requests
        with patch("aiohttp.ClientSession.request", side_effect=mock_aiohttp_request):
            async with PerificAPI(email, token) as api:
                await run_tests(api)
    else:
        print("🔧 Testing Perific API with real credentials...")
        print(f"📧 Email: {email}")
        print(f"🔑 Token: {token[:20]}...")

        async with PerificAPI(email, token) as api:
            await run_tests(api)


async def run_tests(api):
    """Run the actual tests."""
    try:
        print("\n📋 Getting user info...")
        try:
            user_info = await api.get_user_info()
            print(f"✅ User: {user_info.get('Email')}")
            print(f"   Name: {user_info.get('Name', 'Unknown')}")
            print(f"   City: {user_info.get('City')}")
            print(f"   Country: {user_info.get('Country')}")
        except Exception as e:
            print(f"❌ User info failed: {e}")
            print("   Token might be expired or invalid")

        print("\n⚡ Getting latest meter packets...")
        packets = await api.get_latest_packets()
        print(f"✅ Found {len(packets)} meter items")

        # Process mock data format
        for packet in packets:
            item_id = packet.get("Id")
            print(f"\n📊 Processing Item {item_id}:")
            print(f"   📌 Name: {packet.get('Name')}")
            print(f"   📌 Type: {packet.get('Type')}")
            print(f"   📌 Subtype: {packet.get('Subtype')}")
            print(f"   📌 MAC: {packet.get('MAC')}")
            print(f"   📌 Timezone: {packet.get('Timezone')}")

            # Show real-time data
            if "PhaseRealTime" in packet:
                phase_data = packet["PhaseRealTime"]
                print(f"   📡 PhaseRealTime:")
                print(f"      🔌 Current (A): {phase_data.get('hiavg', [])}")
                print(f"      ⚡ Voltage (V): {phase_data.get('huavg', [])}")

                # Calculate power
                hiavg = phase_data.get("hiavg", [0, 0, 0])
                huavg = phase_data.get("huavg", [230, 230, 230])

                if len(hiavg) == 3 and len(huavg) == 3:
                    power_phases = [
                        abs(current) * voltage for current, voltage in zip(hiavg, huavg)
                    ]
                    total_power = sum(power_phases)
                    print(f"      🏠 Calculated Power: {total_power:.1f} W")

                print(f"      💾 Firmware: {phase_data.get('firmware')}")
                print(f"      📶 Signal: {phase_data.get('signal')} dBm")

        print("\n✅ All tests completed successfully!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_api())
