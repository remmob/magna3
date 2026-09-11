"""Grundfos MAGNA3 Modbus hub/coordinator.

Grundfos documentation register number X is addressed as X-1 on the wire;
all public APIs of this hub take Grundfos register numbers and subtract 1
internally.

Stuck-link detection: modbus_connection reconnects automatically after a
dropped connection, but a network-to-serial bridge (e.g. a CIM 500 or an
Elfin EW-11) can keep a socket open while the pump behind it stops
responding - the socket looks healthy so nothing triggers a reconnect, and
every read just times out on the same dead link. `_track_timeout` below
detects that pattern (across a whole poll, not per range) and forces a
disconnect so the next poll opens a fresh connection.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from modbus_connection import ModbusError, ModbusTimeoutError, ModbusUnit

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONTROL_BIT_RESET_ALARM,
    GENIBUS_STALE_POLLS,
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

# This many consecutive polls that ended in a timeout means a stuck link: the
# socket is still open but the pump behind it has stopped responding, so
# automatic reconnection has nothing to reconnect. See _track_timeout below.
STUCK_LINK_TIMEOUTS = 3


class Magna3Hub(DataUpdateCoordinator[dict]):
    """Coordinator that polls a MAGNA3 pump over a Modbus unit."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        unit: ModbusUnit,
        scan_interval: int,
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
        self._unit = unit
        self._static_data: dict = {}
        # Number of consecutive polls that ended in a timeout. See
        # _track_timeout() for where this resets and what happens when the
        # counter fills up.
        self._consecutive_timeouts = 0

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

    def start_notifications(self) -> None:
        """Start the quiet-hours release trigger for connection notifications."""
        self._quiet.start()

    def close(self) -> None:
        """Stop the quiet-hours trigger.

        The Modbus connection itself is not ours to close: connection.py
        registered its own teardown (entry.async_on_unload) when the unit was
        set up, whether that is Home Assistant's shared connection or one we
        opened ourselves.
        """
        self._quiet.stop()

    # --- Low-level read/write ----------------------------------------------

    async def _read_range(self, register: int, count: int) -> tuple[list[int] | None, bool]:
        """Read `count` registers starting at Grundfos register number.

        Retries transient failures up to MAX_READ_RETRIES times. Returns
        (registers, timed_out) - timed_out reflects only the final attempt,
        and is used by the caller to track a stuck link across a whole poll.
        """
        address = register - 1
        timed_out = False

        for attempt in range(MAX_READ_RETRIES):
            try:
                registers = await self._unit.read_holding_registers(address, count)
                return registers, False
            except ModbusTimeoutError as err:
                timed_out = True
                _LOGGER.debug(
                    "Attempt %s/%s timed out for range %s-%s: %s",
                    attempt + 1, MAX_READ_RETRIES, register, register + count - 1, err,
                )
            except ModbusError as err:
                timed_out = False
                _LOGGER.debug(
                    "Attempt %s/%s failed for range %s-%s: %s",
                    attempt + 1, MAX_READ_RETRIES, register, register + count - 1, err,
                )
            if attempt < MAX_READ_RETRIES - 1:
                await asyncio.sleep(0.3)

        return None, timed_out

    async def _write_register(self, register: int, value: int) -> bool:
        """Write a single register (Grundfos register number), with retries."""
        address = register - 1

        for attempt in range(MAX_WRITE_RETRIES):
            try:
                await self._unit.write_register(address, int(value) & 0xFFFF)
                _LOGGER.debug("Wrote %s to register %s", value, register)
                return True
            except ModbusError as err:
                _LOGGER.warning(
                    "Attempt %s/%s failed writing register %s: %s",
                    attempt + 1, MAX_WRITE_RETRIES, register, err,
                )
                if attempt < MAX_WRITE_RETRIES - 1:
                    await asyncio.sleep(0.3)

        _LOGGER.error("Write to register %s failed after %s attempts", register, MAX_WRITE_RETRIES)
        return False

    async def _track_timeout(self, timed_out: bool) -> None:
        """Track consecutive timeouts and disconnect once the link looks stuck."""
        if not timed_out:
            self._consecutive_timeouts = 0
            return

        self._consecutive_timeouts += 1
        if self._consecutive_timeouts >= STUCK_LINK_TIMEOUTS:
            _LOGGER.warning(
                "%s consecutive polls timed out; the connection appears "
                "stuck. Disconnecting so the next poll opens a fresh "
                "connection.",
                self._consecutive_timeouts,
            )
            await self._unit.disconnect()
            # Reset to zero, otherwise every following poll would disconnect
            # again and a fresh connection would never get a chance to prove
            # itself.
            self._consecutive_timeouts = 0

    # --- Public write API ---------------------------------------------------

    async def async_write_register(self, register: int, value: int) -> bool:
        """Write a single register and refresh state."""
        success = await self._write_register(register, value)
        if success:
            await self.async_request_refresh()
        return success

    async def _modify_control_bits(self, set_mask: int, clear_mask: int) -> bool:
        """Read-modify-write the ControlBits register."""
        for attempt in range(MAX_WRITE_RETRIES):
            registers, timed_out = await self._read_range(REG_CONTROL_BITS, 1)
            await self._track_timeout(timed_out)
            if registers is None:
                await asyncio.sleep(0.3)
                continue
            current = registers[0]
            new_value = (current | set_mask) & ~clear_mask & 0xFFFF
            if new_value == current:
                return True
            if await self._write_register(REG_CONTROL_BITS, new_value):
                return True
            await asyncio.sleep(0.3)
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
        success = await self._modify_control_bits(
            mask if value else 0,
            0 if value else mask,
        )
        if success:
            await self.async_request_refresh()
        return success

    async def async_reset_alarm(self) -> bool:
        """Reset pump alarms and warnings (pulse the ResetAlarm control bit)."""
        mask = 1 << CONTROL_BIT_RESET_ALARM
        if not await self._modify_control_bits(mask, 0):
            return False
        await asyncio.sleep(0.5)
        # Lower the bit again so the next reset produces a new rising edge
        # (also safe when AutoAckControlBits already lowered it).
        await self._modify_control_bits(0, mask)
        await self.async_request_refresh()
        return True

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

    async def _read_ranges(
        self, ranges: list[tuple[int, int]]
    ) -> tuple[list[int], list[tuple[int, int]]]:
        """Read (start_register, count) ranges, tolerating individual failures."""
        all_registers: list[int] = []
        failed_ranges: list[tuple[int, int]] = []
        any_timeout = False

        for start, count in ranges:
            registers, timed_out = await self._read_range(start, count)
            any_timeout = any_timeout or timed_out
            if registers is not None and len(registers) >= count:
                all_registers.extend(registers[:count])
            else:
                failed_ranges.append((start, count))

        await self._track_timeout(any_timeout)

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

    async def _read_static_data(self) -> None:
        """Read device identification and pump configuration once."""
        _LOGGER.debug("Reading static device data")
        registers, failed = await self._read_ranges(STATIC_READ_RANGES)
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

    async def read_modbus_realtime_data(self) -> tuple[dict | None, list[tuple[int, int]]]:
        """Read all cyclic registers and decode them into the data dict."""
        if not self._static_data:
            await self._read_static_data()

        registers, failed_ranges = await self._read_ranges(READ_RANGES)
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
        return data, failed_ranges

    async def _async_update_data(self) -> dict:
        """Poll the pump, keeping previous values when a range fails."""
        data = {**(self.data or {})}
        realtime, failed_ranges = await self.read_modbus_realtime_data()

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
