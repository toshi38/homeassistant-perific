# Perific/Enegic Energy Meter API Documentation (Corrected)

## Overview

The Perific/Enegic API provides access to energy meter data, user information, and EV charger integration. The API uses HTTP requests with token-based authentication and returns JSON responses.

## Base URL
```
https://api.enegic.com/
```

## Authentication

### Token-based Authentication
The API uses custom header authentication with X-Authorization header.

#### Headers Required
```http
X-Authorization: {token}
Content-Type: application/json
Accept: application/json
```

#### Check User Activation
```http
PUT /isactivated
Content-Type: application/json

{
  "username": "user@example.com"
}
```

Response:
```json
{
  "IsTaken": true,
  "UserIsActivated": true
}
```

#### Token Refresh
```http
PUT /refreshtoken
Content-Type: application/json
X-Authorization: {current_token}

{
  "token": "current_token_value"
}
```

Response:
```json
{
  "TokenInfo": {
    "Token": "<token>",
    "Created": "2025-07-12T04:43:07.877997Z",
    "ValidTo": "2026-07-12T04:43:07.877997Z"
  },
  "User": {
    "UserId": 1060404,
    "Username": "user@example.com",
    "Domain": "Evify",
    "ParentDomain": "Perific",
    "Capabilities": [...]
  }
}
```

## Key Endpoints

### 1. User Information

#### Get User Info
```http
GET /getuserinfo
X-Authorization: {token}
```

Response:
```json
{
  "Organization": "",
  "Email": "user@example.com",
  "FirstName": "John",
  "LastName": "Doe",
  "Address": "Street 123",
  "ZipCode": "12345",
  "City": "City",
  "PhoneNumber": "0123456789",
  "CreationTime": "2024-04-25T10:55:01",
  "CountryCode": "SE"
}
```

#### Get Account Overview
```http
GET /getaccountoverview
X-Authorization: {token}
Content-Type: application/json

{
  "IncludeSharedItems": true
}
```

### 2. Energy Meter Data

#### Get Latest Meter Readings
```http
PUT /getlatestpackets
X-Authorization: {token}
```

Response:
```json
[
  {
    "ItemId": 1714035408660,
    "LatestPackets": {
      "PhaseRealTime": {
        "hdr": 1002,
        "iid": 1714035408660,
        "ts": 1752509560000,
        "seqno": 6554,
        "it": "Phase",
        "pv": 3,
        "fw": "4.5.7",
        "rssi": -83,
        "data": {
          "dv": 2,
          "hiavg": [-5.59, -5.59, -6.09],
          "huavg": [237.2, 238.3, 240]
        }
      },
      "PhaseHour": {
        "data": {
          "dv": 2,
          "hiavg": [-13.14, -12.79, -13.81],
          "himin": [-16.69, -15.69, -16.99],
          "himax": [0, 0, 0],
          "huavg": [240.1, 239.3, 241.9],
          "hwpi": [0, 0, 0],
          "hwpo": [3.168, 3.064, 3.353],
          "hwi": 57142.768,
          "hwo": 221.315
        }
      },
      "PhaseDay": {
        "data": {
          "dv": 2,
          "hiavg": [-4.49, -3.55, -4.82],
          "himin": [-37.59, -37.69, -38.19],
          "himax": [9.5, 14, 12.8],
          "huavg": [237.8, 238.2, 239.9],
          "hwpi": [2.824, 6.508, 2.799],
          "hwpo": [29.409, 29.401, 31.666],
          "hwi": 57136.729,
          "hwo": 143.804
        }
      },
      "PhaseMinute": {
        "data": {
          "dv": 2,
          "hiavg": [-5.66, -5.41, -6.16],
          "himin": [-5.69, -5.49, -6.19],
          "himax": [0, 0, 0],
          "huavg": [237.3, 238.3, 240.4],
          "hwi": 57142.768,
          "hwo": 222.219
        }
      }
    }
  }
]
```

#### Get Time Series Phase Data
```http
POST /getphasedata
X-Authorization: {token}
Content-Type: application/x-www-form-urlencoded

itemId={item_id}&fromDate={from_date}&toDate={to_date}&dataType={data_type}
```

Parameters:
- `itemId`: Meter item ID
- `fromDate`: Start date (ISO format)
- `toDate`: End date (ISO format)
- `dataType`: Data type (e.g., "Avg", "Min", "Max")

Response:
```json
[
  {
    "dt": "2025-01-01T00:00:00",
    "data": [
      {
        "ts": "2025-07-14T16:13:00",
        "data": {
          "dv": 2,
          "hiavg": [-22.79, -22.29, -23.59],
          "huavg": [243.1, 244.5, 245.4]
        }
      }
    ]
  }
]
```

### 3. Device Information

#### Get Device Parameters
```http
PUT /getitemuserparameters
X-Authorization: {token}
Content-Type: application/json

{
  "itemId": 123456789
}
```

Response:
```json
{
  "DesiredParameters": {},
  "ActualParameters": {
    "ItemId": 123456789,
    "ItemSubType": "EM2One",
    "UserId": 987654321,
    "Name": "Energy Meter",
    "SystemName": "Energy Meter",
    "ItemCategory": "LocalPhysical",
    "TimeZone": "Europe/Stockholm",
    "ItemType": "Phase",
    "Mac": "aa:bb:cc:dd:ee:ff"
  }
}
```

### 4. EV Charger Integration

#### Get Reporter Settings
```http
GET /getreporterssettingsforuser
X-Authorization: {token}
```

Response:
```json
{
  "ZaptecReporters": [
    {
      "ReporterId": 1714035493385,
      "InstallationId": "f79458b7-21d9-43ef-bc45-29fc9747e80d",
      "UserId": 1060404,
      "AlgorithmType": "Simple",
      "SimpleSettings": {
        "PhaseCurrentOverride": [-1, -1, -1],
        "ItemId": 1714035408660,
        "MainsFuseLevel": 25,
        "ChargerFuseLevel": 25,
        "AllowedCurrent": 0,
        "SafeModeCurrent": 6,
        "DelayResume": 5,
        "UseSchema": false,
        "Test": false,
        "SensorType": 8,
        "TimeZone": "Europe/Stockholm"
      },
      "UserSettings": {
        "Mode": "Price",
        "PreviousMode": "Open",
        "DoNotSend": false,
        "SolarSettings": {
          "SolarMaxLevel": 4,
          "SolarStartLevel": -4,
          "Enabled": true
        }
      }
    }
  ],
  "EaseeReporters": [],
  "MontaReporters": [],
  "OpenReporters": [],
  "WallboxReporters": [],
  "AminaReporters": [],
  "OcppReporters": []
}
```


## Data Field Reference

### Phase Data Fields

- **`hiavg`**: Average current per phase [L1, L2, L3] in Amperes
  - Negative values = import/consumption
  - Positive values = export/production
- **`huavg`**: Average voltage per phase [L1, L2, L3] in Volts
- **`hwi`**: Total energy imported in kWh
- **`hwo`**: Total energy exported in kWh
- **`hwpi`**: Power imported per phase [L1, L2, L3] in kW
- **`hwpo`**: Power exported per phase [L1, L2, L3] in kW
- **`himin`/`himax`**: Min/max current values per phase
- **`ts`**: Timestamp (Unix milliseconds)
- **`dv`**: Data version
- **`rssi`**: Signal strength in dBm
- **`fw`**: Firmware version

### Packet Types

- **`PhaseRealTime`**: Most recent readings (updated frequently)
- **`PhaseMinute`**: Minute-averaged values
- **`PhaseHour`**: Hour-averaged values
- **`PhaseDay`**: Day-averaged values with min/max

## Power Calculations

To calculate total power consumption:
```javascript
// From hiavg (current) and huavg (voltage)
const totalPower = hiavg.reduce((sum, current, index) => {
  return sum + Math.abs(current) * huavg[index];
}, 0);

// Or directly from hwpi/hwpo if available
const importPower = hwpi.reduce((sum, power) => sum + power, 0) * 1000; // Convert kW to W
const exportPower = hwpo.reduce((sum, power) => sum + power, 0) * 1000; // Convert kW to W
```

## Error Handling

The API returns standard HTTP status codes:
- `200`: Success
- `400`: Bad Request
- `401`: Unauthorized (invalid token)
- `404`: Not Found
- `500`: Internal Server Error

## Rate Limiting

The API doesn't appear to have strict rate limiting, but the app typically:
- Polls `/getlatestpackets` every 30-60 seconds
- Polls `/getphasedata` less frequently for historical data
- Refreshes tokens as needed

## Best Practices

1. **Token Management**: Store tokens securely and refresh before expiration
2. **Data Polling**: Use appropriate intervals (30-60 seconds for real-time data)
3. **Error Handling**: Implement retry logic with exponential backoff
4. **Data Parsing**: Handle missing fields gracefully as not all meters provide all data
5. **Time Zones**: Be aware of timezone settings in device parameters

## Home Assistant Integration Notes

For Home Assistant integration:
1. Use `/getlatestpackets` for real-time sensor data
2. Parse `PhaseRealTime` or `PhaseMinute` packets for current values
3. Use `PhaseHour` or `PhaseDay` for energy totals
4. Implement proper token refresh mechanism
5. Handle multiple meters per account if needed
6. Convert units appropriately (kW to W, etc.)

The API uses HTTP polling instead of WebSocket connections for real-time data updates.