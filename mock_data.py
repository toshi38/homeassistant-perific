"""Mock data for Perific API testing."""

MOCK_USER_INFO = {
    "Id": 12345,
    "Email": "test@example.com",
    "Name": "Test User",
    "City": "Test City",
    "Country": "ROW",
}

MOCK_ACTIVATION_RESPONSE = {"UserIsActivated": True}

MOCK_TOKEN_RESPONSE = {"token": "mock-token-12345", "expires": "2025-07-15T12:00:00Z"}

MOCK_LATEST_PACKETS = [
    {
        "Id": 1714035408660,
        "Name": "Test Energy Meter",
        "Type": "Phase",
        "Subtype": "EM2One",
        "MAC": "a0:b7:65:6b:96:2c",
        "Timezone": "Europe/Stockholm",
        "PhaseRealTime": {
            "hiavg": [-2.79, -2.49, -2.89],  # Current (A)
            "huavg": [237.3, 237.1, 238.0],  # Voltage (V)
            "firmware": "4.5.7",
            "signal": -84,
        },
    }
]

MOCK_PHASE_DATA = {
    "1714035408660": {"imported": 12.13, "exported": 90.48, "net": -78.34}
}


def get_mock_response(url: str, method: str = "GET") -> dict:
    """Get mock response based on URL and method."""
    if "/userinfo" in url:
        return MOCK_USER_INFO
    elif "/isactivated" in url:
        return MOCK_ACTIVATION_RESPONSE
    elif "/refreshtoken" in url:
        return MOCK_TOKEN_RESPONSE
    elif "/getlatestpackets" in url:
        return MOCK_LATEST_PACKETS
    elif "/getphasedata" in url:
        return MOCK_PHASE_DATA
    else:
        return {"error": "Unknown endpoint"}
