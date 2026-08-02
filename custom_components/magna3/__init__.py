"""Grundfos MAGNA3 Modbus integration (CIM 200 RTU / CIM 500 TCP)."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant

from .alarm_monitor import AlarmMonitor
from .const import (
    CONF_ALARM_DELAY,
    CONF_ALARM_QUIET_ENABLED,
    CONF_ALARM_QUIET_END,
    CONF_ALARM_QUIET_START,
    CONF_ALARM_SERVICES,
    CONF_ALARM_TITLE,
    CONF_BAUDRATE,
    CONF_BYTESIZE,
    CONF_CONNECTION_ERROR_DELAY,
    CONF_CONNECTION_QUIET_ENABLED,
    CONF_CONNECTION_QUIET_END,
    CONF_CONNECTION_QUIET_START,
    CONF_CONNECTION_SERVICES,
    CONF_CONNECTION_TITLE,
    CONF_DEVICE,
    CONF_DEVICE_ID,
    CONF_MODE,
    CONF_NOTIFY_ALARMS,
    CONF_NOTIFY_CONNECTION,
    CONF_NOTIFY_PERSISTENT,
    CONF_NOTIFY_RECOVERY,
    CONF_NOTIFY_SERVICES,
    CONF_NOTIFY_WARNINGS,
    CONF_PARITY,
    CONF_STOPBITS,
    CONF_WARNING_DELAY,
    CONF_WARNING_QUIET_ENABLED,
    CONF_WARNING_QUIET_END,
    CONF_WARNING_QUIET_START,
    CONF_CONNECTION_NOTIFY_RECOVERY,
    CONF_ALARM_NOTIFY_RECOVERY,
    CONF_WARNING_NOTIFY_RECOVERY,
    CONF_WARNING_SERVICES,
    CONF_WARNING_TITLE,
    DEFAULT_ALARM_DELAY,
    DEFAULT_ALARM_TITLE,
    DEFAULT_BAUDRATE,
    DEFAULT_BYTESIZE,
    DEFAULT_CONNECTION_ERROR_DELAY,
    DEFAULT_CONNECTION_TITLE,
    DEFAULT_DEVICE_ID,
    DEFAULT_NAME,
    DEFAULT_NOTIFY_ALARMS,
    DEFAULT_NOTIFY_CONNECTION,
    DEFAULT_NOTIFY_PERSISTENT,
    DEFAULT_NOTIFY_RECOVERY,
    DEFAULT_NOTIFY_SERVICES,
    DEFAULT_NOTIFY_WARNINGS,
    DEFAULT_PARITY,
    DEFAULT_PORT,
    DEFAULT_QUIET_HOURS_ENABLED,
    DEFAULT_QUIET_HOURS_END,
    DEFAULT_QUIET_HOURS_START,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_STOPBITS,
    DEFAULT_WARNING_DELAY,
    DEFAULT_WARNING_TITLE,
    DOMAIN,
    MODE_TCP,
    PLATFORMS,
)
from .hub import Magna3Hub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the MAGNA3 integration from a config entry."""
    data = entry.data
    name = data.get(CONF_NAME, DEFAULT_NAME)

    # Per-category mobile services; entries from before the split fall back to
    # the old shared list so nobody silently stops receiving notifications.
    legacy_services = data.get(CONF_NOTIFY_SERVICES, DEFAULT_NOTIFY_SERVICES)
    connection_services = data.get(CONF_CONNECTION_SERVICES, legacy_services)
    alarm_services = data.get(CONF_ALARM_SERVICES, legacy_services)
    warning_services = data.get(CONF_WARNING_SERVICES, legacy_services)

    # Per-category recovery toggle, same legacy fallback.
    legacy_recovery = data.get(CONF_NOTIFY_RECOVERY, DEFAULT_NOTIFY_RECOVERY)
    connection_recovery = data.get(CONF_CONNECTION_NOTIFY_RECOVERY, legacy_recovery)
    alarm_recovery = data.get(CONF_ALARM_NOTIFY_RECOVERY, legacy_recovery)
    warning_recovery = data.get(CONF_WARNING_NOTIFY_RECOVERY, legacy_recovery)

    hub = Magna3Hub(
        hass,
        name=name,
        scan_interval=data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        mode=data.get(CONF_MODE, MODE_TCP),
        device_id=data.get(CONF_DEVICE_ID, DEFAULT_DEVICE_ID),
        host=data.get(CONF_HOST),
        port=data.get(CONF_PORT, DEFAULT_PORT),
        device=data.get(CONF_DEVICE),
        baudrate=data.get(CONF_BAUDRATE, DEFAULT_BAUDRATE),
        bytesize=data.get(CONF_BYTESIZE, DEFAULT_BYTESIZE),
        parity=data.get(CONF_PARITY, DEFAULT_PARITY),
        stopbits=data.get(CONF_STOPBITS, DEFAULT_STOPBITS),
        notify_connection_errors=data.get(
            CONF_NOTIFY_CONNECTION, DEFAULT_NOTIFY_CONNECTION
        ),
        notify_persistent=data.get(CONF_NOTIFY_PERSISTENT, DEFAULT_NOTIFY_PERSISTENT),
        notify_recovery=connection_recovery,
        notify_services=connection_services,
        connection_error_notification_title=data.get(
            CONF_CONNECTION_TITLE, DEFAULT_CONNECTION_TITLE
        ),
        connection_error_delay=data.get(
            CONF_CONNECTION_ERROR_DELAY, DEFAULT_CONNECTION_ERROR_DELAY
        ),
        connection_quiet_enabled=data.get(
            CONF_CONNECTION_QUIET_ENABLED, DEFAULT_QUIET_HOURS_ENABLED
        ),
        connection_quiet_start=data.get(
            CONF_CONNECTION_QUIET_START, DEFAULT_QUIET_HOURS_START
        ),
        connection_quiet_end=data.get(
            CONF_CONNECTION_QUIET_END, DEFAULT_QUIET_HOURS_END
        ),
    )
    await hub.async_config_entry_first_refresh()

    alarm_monitor = AlarmMonitor(
        hass,
        name=name,
        hub=hub,
        notify_alarms=data.get(CONF_NOTIFY_ALARMS, DEFAULT_NOTIFY_ALARMS),
        notify_warnings=data.get(CONF_NOTIFY_WARNINGS, DEFAULT_NOTIFY_WARNINGS),
        alarm_notify_recovery=alarm_recovery,
        warning_notify_recovery=warning_recovery,
        notify_persistent=data.get(CONF_NOTIFY_PERSISTENT, DEFAULT_NOTIFY_PERSISTENT),
        alarm_services=alarm_services,
        warning_services=warning_services,
        alarm_title=data.get(CONF_ALARM_TITLE, DEFAULT_ALARM_TITLE),
        warning_title=data.get(CONF_WARNING_TITLE, DEFAULT_WARNING_TITLE),
        alarm_delay=data.get(CONF_ALARM_DELAY, DEFAULT_ALARM_DELAY),
        warning_delay=data.get(CONF_WARNING_DELAY, DEFAULT_WARNING_DELAY),
        alarm_quiet_enabled=data.get(
            CONF_ALARM_QUIET_ENABLED, DEFAULT_QUIET_HOURS_ENABLED
        ),
        alarm_quiet_start=data.get(CONF_ALARM_QUIET_START, DEFAULT_QUIET_HOURS_START),
        alarm_quiet_end=data.get(CONF_ALARM_QUIET_END, DEFAULT_QUIET_HOURS_END),
        warning_quiet_enabled=data.get(
            CONF_WARNING_QUIET_ENABLED, DEFAULT_QUIET_HOURS_ENABLED
        ),
        warning_quiet_start=data.get(
            CONF_WARNING_QUIET_START, DEFAULT_QUIET_HOURS_START
        ),
        warning_quiet_end=data.get(CONF_WARNING_QUIET_END, DEFAULT_QUIET_HOURS_END),
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "hub": hub,
        "alarm_monitor": alarm_monitor,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    alarm_monitor.start_monitoring()
    hub.start_notifications()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a MAGNA3 config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        stored = hass.data[DOMAIN].pop(entry.entry_id, None)
        if stored:
            stored["alarm_monitor"].stop_monitoring()
            stored["hub"].close()
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
    return unload_ok
