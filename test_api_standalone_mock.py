#!/usr/bin/env python3
"""Standalone test script for Perific API with mock support."""

import asyncio
import os
from unittest.mock import AsyncMock, patch

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Import existing API and mock data
from custom_components.perific.api import PerificAPI
from mock_data import get_mock_response


def mock_aiohttp_request(method, url, **kwargs):
    """Mock aiohttp request for testing."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=get_mock_response(str(url), method))
    mock_response.raise_for_status = AsyncMock()

    # Create async context manager
    async def async_context_manager():
        return mock_response

    mock_context = AsyncMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_response)
    mock_context.__aexit__ = AsyncMock(return_value=None)

    return mock_context


async def test_api():
    """Test the Perific API with mock support."""
    # Check if running in CI mode
    use_mocks = os.getenv("CI") == "true"

    # Load credentials
    email = os.getenv("PERIFIC_EMAIL", "test@example.com")
    token = os.getenv("PERIFIC_TOKEN", "mock-token-12345")

    if not use_mocks and (not email or not token):
        print("❌ Missing credentials!")
        print("   Set environment variables: PERIFIC_EMAIL and PERIFIC_TOKEN")
        return

    if use_mocks:
        print("🔧 Testing Perific API with mocked responses...")
        # Mock the aiohttp session
        with patch("aiohttp.ClientSession.request", side_effect=mock_aiohttp_request):
            api = PerificAPI(email, token)
            await run_tests(api)
            await api.close()
    else:
        print("🔧 Testing Perific API with real credentials...")
        api = PerificAPI(email, token)
        await run_tests(api)
        await api.close()


async def run_tests(api):
    """Run the actual tests."""
    try:
        print(f"📧 Email: {api._username}")
        print(f"🔑 Token: {api._token[:20] if api._token else 'None'}...")

        print("\n📋 Getting user info...")
        user_info = await api.get_user_info()
        print(f"✅ User: {user_info.get('Email')}")
        print(f"   Name: {user_info.get('Name', 'Unknown')}")
        print(f"   City: {user_info.get('City')}")
        print(f"   Country: {user_info.get('Country')}")

        print("\n⚡ Getting latest meter packets...")
        packets = await api.get_latest_packets()
        print(f"✅ Found {len(packets)} meter items")

        # Process packets
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
                print("   📡 PhaseRealTime:")
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
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_api())
