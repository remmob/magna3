"""Alarm and warning monitoring for the Grundfos MAGNA3 integration.

Alarms and warnings are tracked separately: each has its own confirmation
delay, notification title and quiet-hours window. Persistent notifications are
always sent immediately; mobile notifications are routed through the matching
QuietHours instance so they can be held overnight.
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .notifications import QuietHours, parse_services, send_mobile, send_persistent

_LOGGER = logging.getLogger(__name__)

# code_key -> (text_key in hub data, notification "kind" used for the id/message)
MONITORED = {
    "alarm_code": ("alarm_text", "alarm"),
    "warning_code": ("warning_text", "warning"),
}


class AlarmMonitor:
    """Watch AlarmCode/WarningCode transitions and send notifications."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        hub,
        notify_alarms: bool = True,
        notify_warnings: bool = True,
        alarm_notify_recovery: bool = True,
        warning_notify_recovery: bool = True,
        notify_persistent: bool = True,
        alarm_services: str = "",
        warning_services: str = "",
        alarm_title: str = "MAGNA3 alarm!",
        warning_title: str = "MAGNA3 warning",
        alarm_delay: int = 10,
        warning_delay: int = 10,
        alarm_quiet_enabled: bool = False,
        alarm_quiet_start=None,
        alarm_quiet_end=None,
        warning_quiet_enabled: bool = False,
        warning_quiet_start=None,
        warning_quiet_end=None,
    ) -> None:
        self.hass = hass
        self.name = name
        self._hub = hub
        self._notify_enabled = {
            "alarm_code": notify_alarms,
            "warning_code": notify_warnings,
        }
        self._titles = {"alarm_code": alarm_title, "warning_code": warning_title}
        self._delays = {"alarm_code": alarm_delay, "warning_code": warning_delay}
        self._services = {
            "alarm_code": parse_services(alarm_services),
            "warning_code": parse_services(warning_services),
        }
        self._notify_recovery = {
            "alarm_code": alarm_notify_recovery,
            "warning_code": warning_notify_recovery,
        }
        self._notify_persistent = notify_persistent
        self._last_codes: dict[str, int | None] = {}
        self._notified_codes: dict[str, int] = {}
        self._remove_listener = None

        # A separate quiet-hours window per category.
        self._quiet = {
            "alarm_code": QuietHours(
                hass,
                f"{name} alarm",
                alarm_quiet_enabled,
                alarm_quiet_start,
                alarm_quiet_end,
                self._mobile_sender("alarm_code"),
            ),
            "warning_code": QuietHours(
                hass,
                f"{name} warning",
                warning_quiet_enabled,
                warning_quiet_start,
                warning_quiet_end,
                self._mobile_sender("warning_code"),
            ),
        }

    def _mobile_sender(self, code_key: str):
        """Return a coroutine that sends mobile notifications for this category."""

        async def _send(message: str) -> None:
            await send_mobile(
                self.hass, self._services[code_key], self._titles[code_key], message
            )

        return _send

    def start_monitoring(self) -> None:
        """Start listening to hub data updates."""
        if not any(self._notify_enabled.values()):
            _LOGGER.debug("Alarm/warning notifications disabled, monitor not started")
            return
        for code_key, quiet in self._quiet.items():
            if self._notify_enabled[code_key]:
                quiet.start()
        self._remove_listener = self._hub.async_add_listener(self._handle_hub_update)
        _LOGGER.info("Started MAGNA3 alarm monitoring for %s", self.name)

    def stop_monitoring(self) -> None:
        """Stop listening to hub data updates."""
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None
        for quiet in self._quiet.values():
            quiet.stop()

    @callback
    def _handle_hub_update(self) -> None:
        data = self._hub.data
        if not isinstance(data, dict):
            return

        for code_key in MONITORED:
            new_code = data.get(code_key)
            if new_code is None:
                continue
            old_code = self._last_codes.get(code_key)
            self._last_codes[code_key] = new_code

            if not self._notify_enabled[code_key]:
                continue

            if new_code != 0 and old_code in (0, None) and old_code is not None:
                # Re-check after the configured delay to skip transient codes.
                self.hass.loop.call_later(
                    self._delays[code_key],
                    lambda key=code_key, code=new_code: self.hass.async_create_task(
                        self._maybe_notify(key, code)
                    ),
                )
            elif new_code == 0 and old_code not in (0, None):
                self._handle_recovery(code_key)

    async def _maybe_notify(self, code_key: str, code: int) -> None:
        """Notify if the alarm/warning is still active after the delay."""
        data = self._hub.data
        if not isinstance(data, dict) or data.get(code_key) != code:
            _LOGGER.debug("%s %s cleared before the notification delay", code_key, code)
            return

        text_key, _ = MONITORED[code_key]
        description = data.get(text_key) or f"code {code}"
        message = f"{self.name}: {description} (code {code})"
        self._notified_codes[code_key] = code
        await self._send(code_key, message)

    def _handle_recovery(self, code_key: str) -> None:
        was_notified = code_key in self._notified_codes
        self._notified_codes.pop(code_key, None)
        # A held mobile notification is no longer relevant once the code cleared.
        self._quiet[code_key].clear_held()
        if not self._notify_recovery[code_key] or not was_notified:
            return
        _, kind = MONITORED[code_key]
        message = f"{self.name}: {kind} resolved"
        self.hass.async_create_task(self._send(code_key, message))

    async def _send(self, code_key: str, message: str) -> None:
        """Persistent immediately, mobile through the category's quiet hours."""
        _, kind = MONITORED[code_key]
        if self._notify_persistent:
            send_persistent(
                self.hass, self.name, message, self._titles[code_key], kind
            )
        await self._quiet[code_key].deliver(message)
