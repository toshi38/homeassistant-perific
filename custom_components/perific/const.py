"""Constants for the Perific integration."""
from datetime import timedelta

DOMAIN = "perific"

# API endpoints
API_BASE_URL = "https://api.enegic.com"
API_IS_ACTIVATED = "/isactivated"
API_REFRESH_TOKEN = "/refreshtoken"
API_USER_INFO = "/getuserinfo"
API_ACCOUNT_OVERVIEW = "/getaccountoverview"
API_LATEST_PACKETS = "/getlatestpackets"
API_PHASE_DATA = "/getphasedata"
API_ITEM_PARAMETERS = "/getitemuserparameters"
API_REPORTER_SETTINGS = "/getreporterssettingsforuser"

# Update intervals
SCAN_INTERVAL_POWER = timedelta(seconds=30)
SCAN_INTERVAL_ENERGY = timedelta(minutes=5)

# Sensor types
SENSOR_TYPE_POWER = "power"
SENSOR_TYPE_ENERGY = "energy"
SENSOR_TYPE_VOLTAGE = "voltage"
SENSOR_TYPE_CURRENT = "current"
SENSOR_TYPE_POWER_FACTOR = "power_factor"
SENSOR_TYPE_FREQUENCY = "frequency"

# Units
UNIT_POWER = "W"
UNIT_ENERGY = "kWh"
UNIT_VOLTAGE = "V"
UNIT_CURRENT = "A"
UNIT_FREQUENCY = "Hz"

# Attributes
ATTR_ITEM_ID = "item_id"
ATTR_ITEM_NAME = "item_name"
ATTR_PHASE_L1 = "phase_l1"
ATTR_PHASE_L2 = "phase_l2"
ATTR_PHASE_L3 = "phase_l3"
ATTR_TOTAL = "total"
ATTR_IMPORTED = "imported"
ATTR_EXPORTED = "exported"
ATTR_FIRMWARE = "firmware"
ATTR_SIGNAL_STRENGTH = "signal_strength"
ATTR_TIMESTAMP = "timestamp"

