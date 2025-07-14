#!/usr/bin/env python3
"""Test the datetime fix for timezone comparison."""

import asyncio
from datetime import datetime, timedelta, timezone
from custom_components.perific.api import PerificAPI

async def test_datetime_fix():
    """Test that datetime comparison works with timezone-aware datetimes."""
    print("🔧 Testing datetime fix...")
    
    # Create API instance
    api = PerificAPI("test@example.com", "test-token")
    
    # Simulate a timezone-aware token expiration time
    api._token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    api._token = "test-token"
    
    print(f"Token expires: {api._token_expires}")
    print(f"Current time (UTC): {datetime.now(timezone.utc)}")
    
    try:
        # This should not raise a TypeError anymore
        await api._ensure_authenticated()
        print("✅ Datetime comparison works correctly!")
        
    except TypeError as e:
        if "offset-naive and offset-aware datetimes" in str(e):
            print(f"❌ Datetime fix failed: {e}")
        else:
            print(f"❌ Unexpected error: {e}")
    except Exception as e:
        # Other exceptions are expected (no real API connection)
        print(f"✅ Datetime comparison works (other error expected): {type(e).__name__}")
    
    await api.close()

if __name__ == "__main__":
    asyncio.run(test_datetime_fix())