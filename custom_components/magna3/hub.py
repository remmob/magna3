"""Grundfos MAGNA3 Modbus hub/coordinator.

Grundfos documentation register number X is addressed as X-1 on the wire;
all public APIs of this hub take Grundfos register numbers and subtract 1
internally.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta

from pymodbus.client import ModbusSerialClient, ModbusTcpClient
from pymodbus.exceptions import ConnectionException, ModbusIOException

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONTROL_BIT_RESET_ALARM,
    GENIBUS_STALE_POLLS,
    MODE_SERIAL,
    READ_RANGES,
    REG_ALARM_CODE,
    REG_CONTROL_BITS,
    REG_STATUS_BITS,
    REG_WARNING_CODE,
    REGISTER_NOT_AVAILABLE,
    SENSOR_TYPES,
    STATIC_READ_RANGES,
    STATUS_BITS,
    U32_PAIRS,
    alarm_code_text,
    status_bit_key,
)
from .notifications import QuietHours, parse_services, send_mobile, send_persistent

_LOGGER = logging.getLogger(__name__)

MAX_READ_RETRIES = 3
MAX_WRITE_RETRIES = 2
STALE_CONNECTION_SECONDS = 300


class Magna3Hub(DataUpdateCoordinator[dict]):
    """Thread-safe pymodbus wrapper and data coordinator for a MAGNA3 pump."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        scan_interval: int,
        mode: str,
        device_id: int,
        host: str | None = None,
        port: int | None = None,
        device: str | None = None,
        baudrate: int | None = None,
        bytesize: int | None = None,
        parity: str | None = None,
        stopbits: int | None = None,
        notify_connection_errors: bool = False,
        notify_persistent: bool = True,
        notify_recovery: bool = True,
        notify_services: str = "",
        connection_error_notification_title: str = "MAGNA3 connection error!",
        connection_error_delay: int = 300,
        connection_quiet_enabled: bool = False,
        connection_quiet_start=None,
        connection_quiet_end=None,
    ) -> None:
        super().__init__(
            hass, _LOGGER, name=name, update_interval=timedelta(seconds=scan_interval)
        )
        self._mode = mode
        self._unit = int(device_id)
        self._host = host
        self._port = int(port) if port is not None else None
        self._device = device
        self._baudrate = int(baudrate) if baudrate is not None else None
        self._bytesize = int(bytesize) if bytesize is not None else None
        self._parity = parity
        self._stopbits = int(stopbits) if stopbits is not None else None

        self._client = None
        self._lock = threading.Lock()
        self._modbus_lock = threading.Lock()
        self._static_data: dict = {}
        self._last_successful_read: datetime | None = None

        self._notify_connection_errors = notify_connection_errors
        self._notify_persistent = notify_persistent
        self._notify_recovery = notify_recovery
        self._notify_services = parse_services(notify_services)
        self._connection_error_notification_title = connection_error_notification_title
        self._consecutive_failures = 0
        self._connection_error_notified = False
        self._connection_lost_time: datetime | None = None
        self._failures_for_delay = max(1, int(connection_error_delay / scan_interval))

        # Connection notifications share one quiet-hours window.
        self._quiet = QuietHours(
            hass,
            f"{name} connection",
            connection_quiet_enabled,
            connection_quiet_start,
            connection_quiet_end,
            self._send_connection_mobile,
        )

        self._last_genibus_rx: int | None = None
        self._genibus_stale_polls = 0
        self._genibus_notified = False

        self._client = self._create_client()

    # --- Client management -------------------------------------------------

    def _create_client(self):
        if self._mode == MODE_SERIAL:
            _LOGGER.debug(
                "Modbus serial client for %s (baudrate=%s, parity=%s, stopbits=%s)",
                self._device,
                self._baudrate,
                self._parity,
                self._stopbits,
            )
            return ModbusSerialClient(
                port=self._device,
                baudrate=self._baudrate,
                bytesize=self._bytesize,
                parity=self._parity,
                stopbits=self._stopbits,
                timeout=3,
            )
        _LOGGER.debug("Modbus TCP client for %s:%s", self._host, self._port)
        return ModbusTcpClient(host=self._host, port=self._port, timeout=3)

    def _reset_client(self) -> None:
        """Close the current client so the next transaction reconnects."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    def _ensure_connected(self) -> bool:
        if self._client is None or not self._client.connected:
            _LOGGER.debug("Modbus client not connected, attempting reconnect")
            self._reset_client()
            self._client = self._create_client()
            if not self._client.connect():
                _LOGGER.error("Modbus reconnect failed")
                return False
        return True

    def start_notifications(self) -> None:
        """Start the quiet-hours release trigger for connection notifications."""
        self._quiet.start()

    def close(self) -> None:
        """Disconnect the Modbus client."""
        self._quiet.stop()
        try:
            with self._lock:
                self._reset_client()
            _LOGGER.debug("Modbus client connection closed")
        except Exception as err:
            _LOGGER.exception("Error closing Modbus connection: %s", err)

    # --- Low-level read/write ----------------------------------------------

    def _read_registers(self, register: int, count: int):
        """Read `count` registers starting at Grundfos register number."""
        address = register - 1
        try:
            if not self._ensure_connected():
                return None
            with self._modbus_lock:
                response = self._client.read_holding_registers(
                    address=address, count=count, device_id=self._unit
                )
            if response is None or not hasattr(response, "registers"):
                return None
            if response.isError():
                _LOGGER.warning("Forcing reconnect due to Modbus error frame")
                self._reset_client()
                return None
            return response
        except (ConnectionException, ModbusIOException, OSError) as err:
            _LOGGER.error(
                "Modbus communication error reading %s-%s: %s",
                register,
                register + count - 1,
                err,
            )
            self._reset_client()
            return None
        except Exception as err:
            _LOGGER.exception(
                "Unexpected error reading %s-%s: %s", register, register + count - 1, err
            )
            return None

    def _write_register_sync(self, register: int, value: int) -> bool:
        """Write a single register (Grundfos register number)."""
        address = register - 1
        try:
            if not self._ensure_connected():
                return False
            with self._modbus_lock:
                response = self._client.write_register(
                    address=address, value=int(value) & 0xFFFF, device_id=self._unit
                )
            if response is None or response.isError():
                _LOGGER.error("Write to register %s failed", register)
                self._reset_client()
                return False
            _LOGGER.debug("Wrote %s to register %s", value, register)
            return True
        except (ConnectionException, ModbusIOException, OSError) as err:
            _LOGGER.error("Modbus communication error writing %s: %s", register, err)
            self._reset_client()
            return False
        except Exception as err:
            _LOGGER.exception("Unexpected error writing %s: %s", register, err)
            return False

    # --- Public write API ---------------------------------------------------

    async def async_write_register(self, register: int, value: int) -> bool:
        """Write a single register and refresh state."""
        success = await self.hass.async_add_executor_job(
            self._write_register_sync, register, value
        )
        if success:
            await self.async_request_refresh()
        return success

    def _modify_control_bits_sync(self, set_mask: int, clear_mask: int) -> bool:
        """Read-modify-write the ControlBits register."""
        for attempt in range(MAX_WRITE_RETRIES):
            response = self._read_registers(REG_CONTROL_BITS, 1)
            if response is None:
                time.sleep(0.3)
                continue
            current = response.registers[0]
            new_value = (current | set_mask) & ~clear_mask & 0xFFFF
            if new_value == current:
                return True
            if self._write_register_sync(REG_CONTROL_BITS, new_value):
                return True
            time.sleep(0.3)
        _LOGGER.error(
            "Failed to modify control bits after %s attempts (set=%s, clear=%s)",
            MAX_WRITE_RETRIES,
            set_mask,
            clear_mask,
        )
        return False

    async def async_set_control_bit(self, bit: int, value: bool) -> bool:
        """Set or clear a single ControlBits bit and refresh state."""
        mask = 1 << bit
        success = await self.hass.async_add_executor_job(
            self._modify_control_bits_sync,
            mask if value else 0,
            0 if value else mask,
        )
        if success:
            await self.async_request_refresh()
        return success

    def _reset_alarm_sync(self) -> bool:
        """Pulse the ResetAlarm control bit (triggered on rising edge)."""
        mask = 1 << CONTROL_BIT_RESET_ALARM
        if not self._modify_control_bits_sync(mask, 0):
            return False
        time.sleep(0.5)
        # Lower the bit again so the next reset produces a new rising edge
        # (also safe when AutoAckControlBits already lowered it).
        self._modify_control_bits_sync(0, mask)
        return True

    async def async_reset_alarm(self) -> bool:
        """Reset pump alarms and warnings."""
        success = await self.hass.async_add_executor_job(self._reset_alarm_sync)
        if success:
            await self.async_request_refresh()
        return success

    @property
    def is_remote_controlled(self) -> bool:
        """Return True if the pump currently accepts remote (Modbus) control."""
        data = self.data or {}
        return bool(data.get(status_bit_key(8)))

    @property
    def static_data(self) -> dict:
        """Return the static device data read at startup."""
        return self._static_data

    # --- Reading ------------------------------------------------------------

    def _read_ranges(
        self, ranges: list[tuple[int, int]]
    ) -> tuple[list[int], list[tuple[int, int]]]:
        """Read (start_register, count) ranges with retries per range."""
        all_registers: list[int] = []
        failed_ranges: list[tuple[int, int]] = []

        for start, count in ranges:
            success = False
            for attempt in range(MAX_READ_RETRIES):
                response = self._read_registers(start, count)
                if response is not None and len(response.registers) >= count:
                    all_registers.extend(response.registers[:count])
                    success = True
                    break
                _LOGGER.debug(
                    "Attempt %s failed for range %s-%s",
                    attempt + 1,
                    start,
                    start + count - 1,
                )
                time.sleep(0.3)
            if not success:
                failed_ranges.append((start, count))

        if failed_ranges:
            _LOGGER.warning(
                "Some register ranges failed: %s. Proceeding with available data.",
                failed_ranges,
            )
        return all_registers, failed_ranges

    @staticmethod
    def _build_register_map(
        ranges: list[tuple[int, int]], failed_ranges: list[tuple[int, int]]
    ) -> dict[int, int]:
        """Map Grundfos register number -> index in the flat register list."""
        register_map: dict[int, int] = {}
        index = 0
        for start, count in ranges:
            if (start, count) in failed_ranges:
                continue
            for offset in range(count):
                register_map[start + offset] = index
                index += 1
        return register_map

    @staticmethod
    def _format_bcd_version(hi: int | None, lo: int | None) -> str | None:
        """Format the product software version from two BCD registers."""
        if not hi:
            return None
        parts = [f"{(hi >> 8) & 0xFF:02x}", f"{hi & 0xFF:02x}"]
        if lo:
            parts += [f"{(lo >> 8) & 0xFF:02x}", f"{lo & 0xFF:02x}"]
        return ".".join(str(int(p, 16)) for p in parts)

    def _read_static_data(self) -> None:
        """Read device identification and pump configuration once."""
        _LOGGER.debug("Reading static device data")
        registers, failed = self._read_ranges(STATIC_READ_RANGES)
        if len(failed) == len(STATIC_READ_RANGES):
            return
        register_map = self._build_register_map(STATIC_READ_RANGES, failed)

        def reg(number: int) -> int | None:
            if number not in register_map:
                return None
            value = registers[register_map[number]]
            return None if value == REGISTER_NOT_AVAILABLE else value

        static = {
            "cim_version": reg(23),
            "modbus_address": reg(24),
            "unit_family": reg(30),
            "unit_type": reg(31),
            "unit_version": reg(32),
            "product_sw_version": self._format_bcd_version(reg(34), reg(35)),
            # Setpoint range in % of sensor maximum (scale 0.01 %).
            "setpoint_min_pct": (reg(215) or 0) * 0.01 if reg(215) is not None else None,
            "setpoint_max_pct": (reg(216) or 0) * 0.01 if reg(216) is not None else None,
            "nominal_frequency": (reg(212) or 0) * 0.1 if reg(212) is not None else None,
        }
        self._static_data = static
        _LOGGER.debug("Static device data: %s", static)

    def read_modbus_realtime_data(self) -> tuple[dict | None, list[tuple[int, int]]]:
        """Read all cyclic registers and decode them into the data dict."""
        if not self._static_data:
            self._read_static_data()

        registers, failed_ranges = self._read_ranges(READ_RANGES)
        if not registers:
            return None, failed_ranges

        register_map = self._build_register_map(READ_RANGES, failed_ranges)

        def raw(number: int) -> int | None:
            if number not in register_map:
                return None
            value = registers[register_map[number]]
            return None if value == REGISTER_NOT_AVAILABLE else value

        data: dict = {}

        # Scaled 16-bit sensor registers.
        for key, description in SENSOR_TYPES.items():
            if not key.isdigit():
                continue
            value = raw(int(key))
            if value is None:
                data[key] = None
                continue
            data[key] = round(
                value * description.scale + description.offset,
                description.suggested_display_precision or 2,
            )

        # 32-bit HI/LO pairs.
        for hi_register, key in U32_PAIRS:
            hi = raw(hi_register)
            lo = raw(hi_register + 1)
            if hi is None and lo is None:
                data[key] = None
                continue
            value = ((hi or 0) << 16) | (lo or 0)
            description = SENSOR_TYPES.get(key)
            scale = description.scale if description else 1.0
            data[key] = round(value * scale, 2) if scale != 1.0 else value

        # Raw control/status/mode registers for switches, selects and numbers.
        for register in (101, 102, 103, 104, 106, 201, 203, 204):
            data[str(register)] = raw(register)

        # Status bits.
        status = raw(REG_STATUS_BITS)
        for bit in STATUS_BITS:
            data[status_bit_key(bit)] = (
                bool(status & (1 << bit)) if status is not None else None
            )

        # Alarm and warning codes with readable text.
        alarm_code = raw(REG_ALARM_CODE)
        warning_code = raw(REG_WARNING_CODE)
        data["alarm_code"] = alarm_code
        data["warning_code"] = warning_code
        data["alarm_text"] = alarm_code_text(alarm_code)
        data["warning_text"] = alarm_code_text(warning_code)

        # Pump link health: the GENIbus RX counter (00027/00028) increments on
        # every telegram the CIM receives from the pump. When it freezes, the
        # CIM is serving stale data even though Modbus itself still works.
        rx_hi = raw(27)
        rx_lo = raw(28)
        if rx_hi is not None or rx_lo is not None:
            rx = ((rx_hi or 0) << 16) | (rx_lo or 0)
            if rx == self._last_genibus_rx:
                self._genibus_stale_polls += 1
            else:
                self._genibus_stale_polls = 0
            self._last_genibus_rx = rx
        data["genibus_ok"] = self._genibus_stale_polls < GENIBUS_STALE_POLLS

        # Values backing the writable number entities.
        user_setpoint = raw(338)
        data["user_setpoint_pct"] = (
            round(user_setpoint * 0.01, 1) if user_setpoint is not None else None
        )
        max_flow = raw(345)
        # Register 00345 is scaled 0.01 m³/h, matching the pump display and the
        # 0.01 write scale on register 00106.
        data["max_flow_limit"] = round(max_flow * 0.01, 2) if max_flow is not None else None

        data.update(self._static_data)
        self._last_successful_read = datetime.now()
        return data, failed_ranges

    async def _async_update_data(self) -> dict:
        """Poll the pump, keeping previous values when a range fails."""
        if self._last_successful_read is not None:
            stale_for = (datetime.now() - self._last_successful_read).total_seconds()
            if stale_for > STALE_CONNECTION_SECONDS:
                _LOGGER.warning(
                    "No successful reads for %ss, forcing reconnect", int(stale_for)
                )
                self._reset_client()

        data = {**(self.data or {})}
        realtime, failed_ranges = await self.hass.async_add_executor_job(
            self.read_modbus_realtime_data
        )

        if realtime is None:
            data["connection_status"] = "Failed"
            await self._handle_connection_failure()
            return data

        data.update(realtime)
        if failed_ranges:
            data["connection_status"] = "Partial"
        else:
            data["connection_status"] = "OK"
            await self._handle_connection_restored()

        if data.get("genibus_ok") is False:
            data["connection_status"] = "No pump data"
        await self._handle_genibus_state(data.get("genibus_ok"))
        return data

    async def _handle_genibus_state(self, genibus_ok: bool | None) -> None:
        """Notify when the CIM loses or regains its internal link to the pump."""
        if genibus_ok is None or not self._notify_connection_errors:
            return

        if not genibus_ok and not self._genibus_notified:
            self._genibus_notified = True
            message = (
                f"{self.name}: pump is not responding to the CIM module; "
                "Modbus data is frozen (check pump power and the CIM/GENIbus link)"
            )
            await self._send_connection_notification(message)
        elif genibus_ok and self._genibus_notified:
            self._genibus_notified = False
            if self._notify_recovery:
                await self._send_connection_notification(
                    f"{self.name}: communication between CIM module and pump restored",
                    recovered=True,
                )

    def _connection_persistent(self, message: str) -> None:
        """Show the connection message as a persistent notification (never held)."""
        if self._notify_persistent:
            send_persistent(
                self.hass,
                self.name,
                message,
                self._connection_error_notification_title,
                "connection_error",
            )

    async def _send_connection_mobile(self, message: str) -> None:
        """Deliver a connection message to the mobile notify services."""
        await send_mobile(
            self.hass,
            self._notify_services,
            self._connection_error_notification_title,
            message,
        )

    async def _send_connection_notification(
        self, message: str, *, recovered: bool = False
    ) -> None:
        """Send a connection message: persistent now, mobile via quiet hours."""
        self._connection_persistent(message)
        if recovered:
            # A pending "lost" notification is moot once we are back.
            self._quiet.clear_held()
        await self._quiet.deliver(message)

    # --- Connection failure notifications ------------------------------------

    async def _handle_connection_failure(self) -> None:
        """Track consecutive failures and notify once the delay has elapsed."""
        self._consecutive_failures += 1
        if self._consecutive_failures == 1:
            self._connection_lost_time = datetime.now()

        if (
            self._consecutive_failures >= self._failures_for_delay
            and self._notify_connection_errors
            and not self._connection_error_notified
        ):
            lost_time = (self._connection_lost_time or datetime.now()).strftime(
                "%d-%m-%Y %H:%M:%S"
            )
            message = f"Communication with {self.name} lost since {lost_time}"
            await self._send_connection_notification(message)
            self._connection_error_notified = True

    async def _handle_connection_restored(self) -> None:
        """Reset failure tracking and optionally announce recovery."""
        was_notified = self._connection_error_notified
        self._consecutive_failures = 0
        self._connection_lost_time = None
        self._connection_error_notified = False

        if was_notified and self._notify_connection_errors and self._notify_recovery:
            await self._send_connection_notification(
                f"Communication with {self.name} restored", recovered=True
            )
