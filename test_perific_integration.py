#!/usr/bin/env python3
"""Test script for Perific API integration (Corrected)."""
import asyncio
import os

from custom_components.perific.api import PerificAPI

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")
    print("   You can also set environment variables manually.")


async def test_api():
    """Test the Perific API."""
    # Load credentials from environment variables or .env file
    email = os.getenv("PERIFIC_EMAIL")
    token = os.getenv("PERIFIC_TOKEN")

    if not email or not token:
        print("❌ Missing credentials!")
        print("   Set environment variables: PERIFIC_EMAIL and PERIFIC_TOKEN")
        print("   Or create a .env file with your credentials")
        print("   See .env.example for format")
        return

    api = PerificAPI(email, token)

    try:
        print("Testing user activation...")
        is_activated = await api.check_activation()
        print(f"✓ User activated: {is_activated}")

        print("\nTesting token refresh...")
        await api.refresh_token()
        print("✓ Token refresh successful")

        print("\nGetting user info...")
        user_info = await api.get_user_info()
        print(f"User: {user_info.get('Email')}")
        print(f"Name: {user_info.get('FirstName')} {user_info.get('LastName')}")
        print(f"City: {user_info.get('City')}")

        print("\nDiscovering items...")
        items = await api.discover_items()
        print(f"Found {len(items)} items")

        for item in items:
            item_id = item["id"]
            item_name = item.get("name", f"Item {item_id}")
            print(f"\n--- {item_name} ({item_id}) ---")
            print(f"Type: {item.get('type')}")
            print(f"Subtype: {item.get('subtype')}")

            # Test current power
            print("Getting current power...")
            power_data = await api.get_current_power(item_id)
            if power_data:
                total_power = power_data.get("power", {}).get("total", 0)
                voltage_l1 = power_data.get("voltage", {}).get("l1", 0)
                current_l1 = power_data.get("current", {}).get("l1", 0)
                print(f"  Total power: {total_power:.1f} W")
                print(f"  Voltage L1: {voltage_l1:.1f} V")
                print(f"  Current L1: {current_l1:.2f} A")
                print(f"  Firmware: {power_data.get('firmware')}")
                print(f"  Signal: {power_data.get('signal_strength')} dBm")
            else:
                print("  No power data available")

            # Test today's energy
            print("Getting today's energy...")
            energy_data = await api.get_energy_today(item_id)
            if energy_data:
                print(f"  Imported: {energy_data.get('imported', 0):.2f} kWh")
                print(f"  Exported: {energy_data.get('exported', 0):.2f} kWh")
                print(f"  Net: {energy_data.get('net', 0):.2f} kWh")
            else:
                print("  No energy data available")

        # Note: Spot prices functionality not implemented in this version
        print("\nSpot prices functionality not implemented in this version")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        await api.close()


if __name__ == "__main__":
    asyncio.run(test_api())
