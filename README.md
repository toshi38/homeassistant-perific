# Perific Energy Meter Home Assistant Integration (Corrected)

This custom integration allows you to monitor your Perific/Enegic energy meter data in Home Assistant.

## Features

- **Real-time power monitoring** - Track current power consumption per phase and total
- **Energy consumption tracking** - Monitor daily imported/exported energy
- **Voltage monitoring** - Monitor voltage levels on all three phases
- **Current monitoring** - Track current draw on each phase
- **Native Home Assistant energy dashboard support**
- **HTTP polling** - Uses standard HTTP requests (no WebSocket dependency)

## Installation

### Manual Installation

1. Copy the `custom_components/perific` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Go to Settings → Devices & Services → Add Integration
4. Search for "Perific Energy Meter"
5. Enter your Perific account email and authentication token

### HACS Installation

1. Add this repository to HACS as a custom repository
2. Install the integration through HACS
3. Restart Home Assistant
4. Add the integration through the UI

## Configuration

The integration is configured through the Home Assistant UI:

1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for "Perific Energy Meter"
4. Enter your Perific account email and authentication token

### Getting Your Authentication Token

To get your authentication token:
1. Log in to the Perific web app
2. Open your browser's developer tools (F12)
3. Go to the Network tab
4. Look for API requests to `api.enegic.com`
5. Find the `X-Authorization` header value - this is your token

## Sensors

For each energy meter item, the integration creates the following sensors:

### Power Sensors
- `sensor.{item_name}_power_total` - Total power consumption
- `sensor.{item_name}_power_l1` - Phase L1 power
- `sensor.{item_name}_power_l2` - Phase L2 power
- `sensor.{item_name}_power_l3` - Phase L3 power

### Energy Sensors
- `sensor.{item_name}_energy_imported` - Today's imported energy
- `sensor.{item_name}_energy_exported` - Today's exported energy
- `sensor.{item_name}_energy_net` - Net energy (imported - exported)

### Voltage Sensors
- `sensor.{item_name}_voltage_l1` - Phase L1 voltage
- `sensor.{item_name}_voltage_l2` - Phase L2 voltage
- `sensor.{item_name}_voltage_l3` - Phase L3 voltage

### Current Sensors
- `sensor.{item_name}_current_l1` - Phase L1 current (absolute value)
- `sensor.{item_name}_current_l2` - Phase L2 current (absolute value)
- `sensor.{item_name}_current_l3` - Phase L3 current (absolute value)

### Additional Attributes
Each sensor includes these additional attributes:
- `firmware` - Device firmware version
- `signal_strength` - Signal strength in dBm
- `timestamp` - Last reading timestamp

## Energy Dashboard Integration

The integration is compatible with Home Assistant's energy dashboard:

1. Go to Settings → Dashboards → Energy
2. Add your energy sensors to track consumption
3. The sensors provide the correct device classes for automatic recognition

## API Documentation

See [PERIFIC_API_DOCUMENTATION.md](PERIFIC_API_DOCUMENTATION.md) for detailed API documentation.

## Testing

### Setup Development Environment

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create your environment file:
```bash
cp .env.example .env
```

3. Edit `.env` with your actual credentials:
```
PERIFIC_EMAIL=your_actual_email@example.com
PERIFIC_TOKEN=your_actual_token_here
```

### Running Tests

Use the provided test scripts to verify your API connection:

```bash
# Test standalone API client
python test_api_standalone.py

# Test Home Assistant integration
python test_perific_integration.py
```

### Getting Your API Token

To get your authentication token:
1. Log in to the Perific web app
2. Open your browser's developer tools (F12)
3. Go to the Network tab
4. Look for API requests to `api.enegic.com`
5. Find the `X-Authorization` header value - this is your token

### Environment Variables

You can also set environment variables directly instead of using a `.env` file:

```bash
export PERIFIC_EMAIL="your_email@example.com"
export PERIFIC_TOKEN="your_token_here"
python test_api_standalone.py
```

## API Structure

The integration uses the real Perific/Enegic API at `https://api.enegic.com/`:
- **Authentication**: X-Authorization header with token
- **Data Updates**: HTTP polling every 30 seconds
- **Data Source**: `/getlatestpackets` endpoint for real-time data
- **Power Calculation**: Calculated from current (hiavg) and voltage (huavg) readings
- **Energy Data**: Daily imported/exported energy from phase data

## Troubleshooting

### Authentication Issues
- Verify your email and password are correct
- Check if your account has access to the meters
- Ensure your internet connection is stable

### Sensor Not Updating
- Check the Home Assistant logs for error messages
- Verify the integration is properly configured
- Restart Home Assistant if needed

### Rate Limiting
- The API has rate limits (1000 requests/hour, 10/second per endpoint)
- The integration respects these limits with appropriate update intervals

## Support

For issues and feature requests, please create an issue in the GitHub repository.

## License

This integration is provided under the MIT License.