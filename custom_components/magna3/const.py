"""Constants for the Grundfos MAGNA3 Modbus integration.

Register numbers follow the Grundfos "Modbus for Grundfos pumps" functional
profile (CIM 200 Modbus RTU / CIM 500 Modbus TCP). Documentation register
number X is addressed as X-1 on the wire, per the Modbus standard; the hub
subtracts 1 when reading/writing.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    REVOLUTIONS_PER_MINUTE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolume,
    UnitOfVolumeFlowRate,
    PERCENTAGE,
)

DOMAIN = "magna3"
PLATFORMS = ["sensor", "binary_sensor", "switch", "select", "number", "button"]

# --- Connection configuration ---
MODE_TCP = "tcp"
MODE_SERIAL = "serial"
MODES = [MODE_TCP, MODE_SERIAL]

CONF_MODE = "mode"
CONF_DEVICE = "device"
CONF_DEVICE_ID = "device_id"
CONF_BAUDRATE = "baudrate"
CONF_BYTESIZE = "bytesize"
CONF_PARITY = "parity"
CONF_STOPBITS = "stopbits"

DEFAULT_NAME = "MAGNA3"
DEFAULT_DEVICE_ID = 1
DEFAULT_PORT = 502
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_BAUDRATE = 19200
DEFAULT_BYTESIZE = 8
DEFAULT_PARITY = "E"
DEFAULT_STOPBITS = 1

ALLOWED_DEVICE_IDS = list(range(1, 248))
ALLOWED_BAUDRATES = [1200, 2400, 4800, 9600, 19200, 38400]
ALLOWED_BYTESIZES = [8]
# CIM 200: even parity + 1 stop bit (default) or no parity + 2 stop bits.
ALLOWED_PARITIES = ["E", "N"]
ALLOWED_STOPBITS = [1, 2]

# --- Notification configuration ---
CONF_NOTIFY_ALARMS = "notify_alarms"
CONF_NOTIFY_WARNINGS = "notify_warnings"
CONF_NOTIFY_RECOVERY = "notify_recovery"
CONF_NOTIFY_PERSISTENT = "notify_persistent"
CONF_NOTIFY_SERVICES = "notify_services"

# Per-category mobile notify services, so e.g. connection errors and filter
# warnings can go to different people. Entries created before the split fall
# back to the shared CONF_NOTIFY_SERVICES value.
CONF_CONNECTION_SERVICES = "connection_notify_services"
CONF_ALARM_SERVICES = "alarm_notify_services"
CONF_WARNING_SERVICES = "warning_notify_services"

# Per-category recovery notifications (fall back to CONF_NOTIFY_RECOVERY).
CONF_CONNECTION_NOTIFY_RECOVERY = "connection_notify_recovery"
CONF_ALARM_NOTIFY_RECOVERY = "alarm_notify_recovery"
CONF_WARNING_NOTIFY_RECOVERY = "warning_notify_recovery"
CONF_ALARM_DELAY = "alarm_delay"
CONF_ALARM_TITLE = "alarm_notification_title"
CONF_WARNING_TITLE = "warning_notification_title"
CONF_NOTIFY_CONNECTION = "notify_connection_errors"
CONF_CONNECTION_ERROR_DELAY = "connection_error_delay"
CONF_CONNECTION_TITLE = "connection_error_notification_title"
CONF_WARNING_DELAY = "warning_delay"

# Per-category quiet hours: hold mobile notifications during a set period and
# deliver them once it ends. Connection, alarm and warning each have their own.
CONF_CONNECTION_QUIET_ENABLED = "connection_quiet_hours_enabled"
CONF_CONNECTION_QUIET_START = "connection_quiet_hours_start"
CONF_CONNECTION_QUIET_END = "connection_quiet_hours_end"
CONF_ALARM_QUIET_ENABLED = "alarm_quiet_hours_enabled"
CONF_ALARM_QUIET_START = "alarm_quiet_hours_start"
CONF_ALARM_QUIET_END = "alarm_quiet_hours_end"
CONF_WARNING_QUIET_ENABLED = "warning_quiet_hours_enabled"
CONF_WARNING_QUIET_START = "warning_quiet_hours_start"
CONF_WARNING_QUIET_END = "warning_quiet_hours_end"

# Collapsible option sections, one per notification category.
SECTION_GENERAL = "general"
SECTION_CONNECTION = "connection"
SECTION_ALARM = "alarm"
SECTION_WARNING = "warning"
SECTION_KEYS = [SECTION_GENERAL, SECTION_CONNECTION, SECTION_ALARM, SECTION_WARNING]

DEFAULT_NOTIFY_ALARMS = True
DEFAULT_NOTIFY_WARNINGS = True
DEFAULT_NOTIFY_RECOVERY = True
DEFAULT_NOTIFY_PERSISTENT = True
DEFAULT_NOTIFY_SERVICES = ""
DEFAULT_ALARM_DELAY = 10
DEFAULT_WARNING_DELAY = 10
DEFAULT_ALARM_TITLE = "MAGNA3 alarm!"
DEFAULT_WARNING_TITLE = "MAGNA3 warning"
DEFAULT_NOTIFY_CONNECTION = True
DEFAULT_CONNECTION_ERROR_DELAY = 300
DEFAULT_CONNECTION_TITLE = "MAGNA3 connection error!"

# Quiet hours defaults (off; a sensible night window when switched on).
DEFAULT_QUIET_HOURS_ENABLED = False
DEFAULT_QUIET_HOURS_START = "23:00:00"
DEFAULT_QUIET_HOURS_END = "07:00:00"

# --- Register numbers (Grundfos documentation numbering, 1-based) ---
REG_CONTROL_BITS = 101
REG_CONTROL_MODE = 102
REG_OPERATION_MODE = 103
REG_SETPOINT = 104
REG_MAX_FLOW_LIMIT = 106

REG_STATUS_BITS = 201
REG_ACTUAL_CONTROL_MODE = 203
REG_ACTUAL_OPERATION_MODE = 204
REG_ALARM_CODE = 205
REG_WARNING_CODE = 206
REG_SETPOINT_RANGE_MIN = 215
REG_SETPOINT_RANGE_MAX = 216

REG_USER_SETPOINT = 338
REG_ACTUAL_MAX_FLOW_LIMIT = 345

# ControlBits (register 00101) bit positions.
CONTROL_BIT_REMOTE_ACCESS = 0
CONTROL_BIT_ON_OFF = 1
CONTROL_BIT_RESET_ALARM = 2
CONTROL_BIT_COPY_TO_LOCAL = 4
CONTROL_BIT_ENABLE_MAX_FLOW_LIMIT = 5

# StatusBits (register 00201) bit positions.
STATUS_BIT_COPY_TO_LOCAL = 1
STATUS_BIT_MAX_FLOW_LIMIT_ENABLED = 2
STATUS_BIT_AT_MAX_POWER = 5
STATUS_BIT_ROTATION = 6
STATUS_BIT_DIRECTION = 7
STATUS_BIT_ACCESS_MODE = 8
STATUS_BIT_ON_OFF = 9
STATUS_BIT_FAULT = 10
STATUS_BIT_WARNING = 11
STATUS_BIT_FORCED_TO_LOCAL = 12
STATUS_BIT_AT_MAX_SPEED = 13
STATUS_BIT_AT_MIN_SPEED = 15

# Status bits exposed in coordinator data as "201_bit<n>" boolean keys.
STATUS_BITS = [
    STATUS_BIT_COPY_TO_LOCAL,
    STATUS_BIT_MAX_FLOW_LIMIT_ENABLED,
    STATUS_BIT_AT_MAX_POWER,
    STATUS_BIT_ROTATION,
    STATUS_BIT_DIRECTION,
    STATUS_BIT_ACCESS_MODE,
    STATUS_BIT_ON_OFF,
    STATUS_BIT_FAULT,
    STATUS_BIT_WARNING,
    STATUS_BIT_FORCED_TO_LOCAL,
    STATUS_BIT_AT_MAX_SPEED,
    STATUS_BIT_AT_MIN_SPEED,
]


def status_bit_key(bit: int) -> str:
    """Return the coordinator data key for a StatusBits bit."""
    return f"{REG_STATUS_BITS}_bit{bit}"


# --- Read ranges (Grundfos register numbers; hub subtracts 1 on the wire) ---
# Blocks must never span unused addresses (exception 0x02).
# Static: read once at setup/reload.
STATIC_READ_RANGES: list[tuple[int, int]] = [
    (23, 2),   # 00023-00024: CIM version number, actual Modbus address
    (30, 7),   # 00030-00036: unit family/type/version, product software version
    (212, 5),  # 00212-00216: nominal/min/max frequency, setpoint range
]
# Cyclic: read every poll.
READ_RANGES: list[tuple[int, int]] = [
    (21, 8),   # 00021-00028: CIM status incl. GENIbus TX/RX counters (staleness check)
    (101, 8),  # 00101-00108: pump control block (actual requested values)
    (201, 8),  # 00201-00208: status bits, feedback, modes, alarm/warning code
    (301, 58),  # 00301-00358: measured pump data
]

# The CIM keeps serving its last known data over Modbus when its internal
# GENIbus link to the pump is down; only the frozen RX counter reveals it.
# After this many polls without RX progress the pump link is reported down.
GENIBUS_STALE_POLLS = 3

REGISTER_NOT_AVAILABLE = 0xFFFF

# --- Enumerations ---
# Control mode (registers 00102/00203). Full documented enum so the select
# always recognizes the reported mode; MAGNA3 uses a subset.
CONTROL_MODES: dict[int, str] = {
    0: "constant_speed",
    1: "constant_frequency",
    3: "constant_head",
    4: "constant_pressure",
    5: "constant_diff_pressure",
    6: "proportional_pressure",
    7: "constant_flow",
    8: "constant_temperature",
    10: "constant_level",
    128: "auto_adapt",
    129: "flow_limit",
    130: "closed_loop_sensor",
}

# Operating mode (registers 00103/00204).
OPERATION_MODES: dict[int, str] = {
    0: "normal",
    4: "minimum",
    6: "maximum",
}

# --- Grundfos alarm/warning codes (registers 00205/00206) ---
ALARM_CODES: dict[int, str] = {
    1: "Leakage current",
    2: "Missing phase",
    3: "External fault signal",
    4: "Too many restarts",
    7: "Too many hardware shutdowns",
    14: "Electronic DC-link protection activated (ERP)",
    16: "Other",
    29: "Turbine operation, impellers forced backwards",
    30: "Change bearings (service information)",
    31: "Change varistor(s) (service information)",
    32: "Overvoltage",
    40: "Undervoltage",
    41: "Undervoltage transient",
    42: "Cut-in fault (dV/dt)",
    45: "Voltage asymmetry",
    48: "Overload",
    49: "Overcurrent",
    50: "Motor protection function, general shutdown (MPF)",
    51: "Blocked motor or pump",
    54: "Motor protection function, 3 sec. limit",
    55: "Motor current protection activated (MCP)",
    56: "Underload",
    57: "Dry running",
    60: "Low input power",
    64: "Overtemperature",
    65: "Motor temperature 1",
    66: "Control electronics temperature high",
    67: "Temperature too high, internal frequency converter module",
    68: "Water temperature high",
    70: "Thermal relay 2 in motor",
    72: "Hardware fault, type 1",
    73: "Hardware shutdown (HSD)",
    76: "Internal communication fault",
    77: "Communication fault, twin-head pump",
    80: "Hardware fault, type 2",
    83: "Verification error, FE parameter area (EEPROM)",
    84: "Memory access error",
    85: "Verification error, BE parameter area (EEPROM)",
    88: "Sensor fault",
    89: "Signal fault, (feedback) sensor 1",
    91: "Signal fault, temperature 1 sensor",
    93: "Signal fault, sensor 2",
    96: "Setpoint signal outside range",
    105: "Electronic rectifier protection activated (ERP)",
    106: "Electronic inverter protection activated (EIP)",
    148: "Motor bearing temperature high (Pt100), drive end",
    149: "Motor bearing temperature high (Pt100), non-drive end",
    155: "Inrush fault",
    156: "Communication fault, internal frequency converter module",
    157: "Real-time clock error",
    161: "Sensor supply fault, 5 V",
    162: "Sensor supply fault, 24 V",
    163: "Measurement fault, motor protection",
    164: "Signal fault, LiqTec sensor",
    165: "Signal fault, analog input 1",
    166: "Signal fault, analog input 2",
    167: "Signal fault, analog input 3",
    175: "Signal fault, temperature 2 sensor",
    176: "Signal fault, temperature 3 sensor",
    190: "Limit exceeded, sensor 1",
    191: "Limit exceeded, sensor 2",
    215: "Soft pressure buildup timeout",
    240: "Lubricate bearings (service information)",
    241: "Motor phase failure",
    242: "Automatic motor model recognition failed",
}


def alarm_code_text(code: int | None) -> str | None:
    """Return the human readable text for an alarm/warning code."""
    if code is None:
        return None
    if code == 0:
        return "OK"
    return ALARM_CODES.get(code, f"Unknown code {code}")


# --- 32-bit register pairs: (HI register number, data key) ---
# LO register is always HI+1. Value = (HI << 16) | LO.
U32_PAIRS: list[tuple[int, str]] = [
    (312, "power"),
    (327, "operating_time"),
    (329, "powered_time"),
    (332, "energy"),
    (334, "starts"),
    (352, "heat_energy"),
    (354, "heat_power"),
    (357, "volume"),
]

KELVIN_OFFSET = -273.15


@dataclass(frozen=True, kw_only=True)
class Magna3SensorEntityDescription(SensorEntityDescription):
    """Sensor description with Modbus scaling metadata."""

    scale: float = 1.0
    offset: float = 0.0


# Keyed by coordinator data key: plain register numbers as strings for 16-bit
# registers, named keys for 32-bit pairs and derived values.
SENSOR_TYPES: dict[str, Magna3SensorEntityDescription] = {
    "301": Magna3SensorEntityDescription(
        key="301",
        translation_key="head",
        native_unit_of_measurement=UnitOfPressure.BAR,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        scale=0.001,
    ),
    "302": Magna3SensorEntityDescription(
        key="302",
        translation_key="flow",
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        scale=0.1,
    ),
    "303": Magna3SensorEntityDescription(
        key="303",
        translation_key="relative_performance",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gauge",
        suggested_display_precision=2,
        scale=0.01,
    ),
    "304": Magna3SensorEntityDescription(
        key="304",
        translation_key="speed",
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:rotate-right",
        suggested_display_precision=0,
    ),
    "305": Magna3SensorEntityDescription(
        key="305",
        translation_key="frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        scale=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    "308": Magna3SensorEntityDescription(
        key="308",
        translation_key="actual_setpoint",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:target",
        suggested_display_precision=2,
        scale=0.01,
    ),
    "309": Magna3SensorEntityDescription(
        key="309",
        translation_key="motor_current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        scale=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "310": Magna3SensorEntityDescription(
        key="310",
        translation_key="dc_link_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        scale=0.1,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    "202": Magna3SensorEntityDescription(
        key="202",
        translation_key="process_feedback",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:chart-line",
        suggested_display_precision=2,
        scale=0.01,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    "316": Magna3SensorEntityDescription(
        key="316",
        translation_key="remote_pressure_1",
        native_unit_of_measurement=UnitOfPressure.BAR,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        scale=0.001,
        entity_registry_enabled_default=False,
    ),
    "321": Magna3SensorEntityDescription(
        key="321",
        translation_key="electronics_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        scale=0.01,
        offset=KELVIN_OFFSET,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "322": Magna3SensorEntityDescription(
        key="322",
        translation_key="liquid_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        scale=0.01,
        offset=KELVIN_OFFSET,
    ),
    "326": Magna3SensorEntityDescription(
        key="326",
        translation_key="specific_energy",
        native_unit_of_measurement="Wh/m³",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        icon="mdi:lightning-bolt-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    "337": Magna3SensorEntityDescription(
        key="337",
        translation_key="remote_temperature_2",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        scale=0.01,
        offset=KELVIN_OFFSET,
        entity_registry_enabled_default=False,
    ),
    "339": Magna3SensorEntityDescription(
        key="339",
        translation_key="differential_pressure",
        native_unit_of_measurement=UnitOfPressure.BAR,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        scale=0.001,
        entity_registry_enabled_default=False,
    ),
    "power": Magna3SensorEntityDescription(
        key="power",
        translation_key="power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    "energy": Magna3SensorEntityDescription(
        key="energy",
        translation_key="energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
    ),
    "operating_time": Magna3SensorEntityDescription(
        key="operating_time",
        translation_key="operating_time",
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        icon="mdi:timer-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "powered_time": Magna3SensorEntityDescription(
        key="powered_time",
        translation_key="powered_time",
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        icon="mdi:power-plug-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    "starts": Magna3SensorEntityDescription(
        key="starts",
        translation_key="starts",
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        icon="mdi:counter",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "volume": Magna3SensorEntityDescription(
        key="volume",
        translation_key="volume",
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.VOLUME,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        scale=0.01,
        entity_registry_enabled_default=False,
    ),
    "heat_energy": Magna3SensorEntityDescription(
        key="heat_energy",
        translation_key="heat_energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    "heat_power": Magna3SensorEntityDescription(
        key="heat_power",
        translation_key="heat_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
    ),
    "alarm_text": Magna3SensorEntityDescription(
        key="alarm_text",
        translation_key="alarm",
        icon="mdi:alert-circle-outline",
    ),
    "warning_text": Magna3SensorEntityDescription(
        key="warning_text",
        translation_key="warning",
        icon="mdi:alert-outline",
    ),
    "connection_status": Magna3SensorEntityDescription(
        key="connection_status",
        translation_key="connection_status",
        icon="mdi:lan-connect",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
}

BINARY_SENSOR_TYPES: list[BinarySensorEntityDescription] = [
    BinarySensorEntityDescription(
        key="genibus_ok",
        translation_key="pump_link",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key=status_bit_key(STATUS_BIT_ROTATION),
        translation_key="running",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    BinarySensorEntityDescription(
        key=status_bit_key(STATUS_BIT_FAULT),
        translation_key="fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    BinarySensorEntityDescription(
        key=status_bit_key(STATUS_BIT_WARNING),
        translation_key="warning",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    BinarySensorEntityDescription(
        key=status_bit_key(STATUS_BIT_AT_MAX_POWER),
        translation_key="at_max_power",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    BinarySensorEntityDescription(
        key=status_bit_key(STATUS_BIT_AT_MAX_SPEED),
        translation_key="at_max_speed",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    BinarySensorEntityDescription(
        key=status_bit_key(STATUS_BIT_AT_MIN_SPEED),
        translation_key="at_min_speed",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    BinarySensorEntityDescription(
        key=status_bit_key(STATUS_BIT_FORCED_TO_LOCAL),
        translation_key="forced_to_local",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
]
