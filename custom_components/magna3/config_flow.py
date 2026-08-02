"""Config flow for the Grundfos MAGNA3 Modbus integration."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import re

import serial.tools.list_ports
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers import selector

from .const import (
    ALLOWED_BAUDRATES,
    ALLOWED_PARITIES,
    ALLOWED_STOPBITS,
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
    MODE_SERIAL,
    MODE_TCP,
    MODES,
    SECTION_ALARM,
    SECTION_CONNECTION,
    SECTION_GENERAL,
    SECTION_KEYS,
    SECTION_WARNING,
)

_LOGGER = logging.getLogger(__name__)


def host_valid(host: str) -> bool:
    """Return True if hostname or IP address is valid."""
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        disallowed = re.compile(r"[^a-zA-Z\d\-]")
        return all(part and not disallowed.search(part) for part in host.split("."))


def _connection_unique_id(data: dict) -> str:
    mode = data[CONF_MODE]
    if mode == MODE_SERIAL:
        return f"{MODE_SERIAL}:{data[CONF_DEVICE]}:{data.get(CONF_DEVICE_ID, DEFAULT_DEVICE_ID)}"
    return f"{MODE_TCP}:{data[CONF_HOST]}:{data[CONF_PORT]}:{data.get(CONF_DEVICE_ID, DEFAULT_DEVICE_ID)}"


def _get_notify_service_options(hass: HomeAssistant) -> list[str]:
    services = hass.services.async_services().get("notify", {})
    return sorted(name for name in services if name != "persistent_notification")


def _services_default(value) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [s.strip() for s in value.split(",") if s.strip()]
    return []


def _normalize_services(value) -> str:
    if isinstance(value, list):
        return ", ".join(str(v).strip() for v in value if str(v).strip())
    return str(value).strip() if value else ""


def _notify_services_selector(hass: HomeAssistant) -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=_get_notify_service_options(hass),
            multiple=True,
            custom_value=True,
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def _device_id_selector():
    """Numeric input box (not a slider) for the Modbus unit ID."""
    return vol.All(
        selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1, max=247, step=1, mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Coerce(int),
    )


def _options_selector(options: list) -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                selector.SelectOptionDict(value=str(opt), label=str(opt))
                for opt in options
            ],
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def _tcp_schema_fields(current: dict) -> dict:
    return {
        vol.Required(CONF_HOST, default=current.get(CONF_HOST, "")): str,
        vol.Required(
            CONF_PORT, default=current.get(CONF_PORT, DEFAULT_PORT)
        ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        vol.Optional(
            CONF_SCAN_INTERVAL,
            default=current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        ): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
    }


def _serial_schema_fields(
    current: dict, serial_ports: list[str], default_device: str
) -> dict:
    return {
        vol.Required(CONF_DEVICE, default=default_device): (
            vol.In(serial_ports) if serial_ports else str
        ),
        vol.Required(
            CONF_BAUDRATE, default=str(current.get(CONF_BAUDRATE, DEFAULT_BAUDRATE))
        ): vol.All(_options_selector(ALLOWED_BAUDRATES), vol.Coerce(int)),
        vol.Required(
            CONF_PARITY, default=current.get(CONF_PARITY, DEFAULT_PARITY)
        ): vol.In(ALLOWED_PARITIES),
        vol.Required(
            CONF_STOPBITS, default=str(current.get(CONF_STOPBITS, DEFAULT_STOPBITS))
        ): vol.All(_options_selector(ALLOWED_STOPBITS), vol.Coerce(int)),
        vol.Optional(
            CONF_SCAN_INTERVAL,
            default=current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        ): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
    }


def _services_field_default(current: dict, key: str) -> list:
    """Per-category services, falling back to the legacy shared list."""
    return _services_default(
        current.get(key, current.get(CONF_NOTIFY_SERVICES, DEFAULT_NOTIFY_SERVICES))
    )


def _recovery_default(current: dict, key: str) -> bool:
    """Per-category recovery toggle, falling back to the legacy shared value."""
    return current.get(key, current.get(CONF_NOTIFY_RECOVERY, DEFAULT_NOTIFY_RECOVERY))


def _general_section(hass: HomeAssistant, current: dict):
    """Settings shared by every notification category."""
    return section(
        vol.Schema(
            {
                vol.Optional(
                    CONF_NOTIFY_PERSISTENT,
                    default=current.get(
                        CONF_NOTIFY_PERSISTENT, DEFAULT_NOTIFY_PERSISTENT
                    ),
                ): bool,
            }
        ),
        {"collapsed": False},
    )


def _connection_section(hass: HomeAssistant, current: dict):
    return section(
        vol.Schema(
            {
                vol.Optional(
                    CONF_NOTIFY_CONNECTION,
                    default=current.get(
                        CONF_NOTIFY_CONNECTION, DEFAULT_NOTIFY_CONNECTION
                    ),
                ): bool,
                vol.Optional(
                    CONF_CONNECTION_NOTIFY_RECOVERY,
                    default=_recovery_default(current, CONF_CONNECTION_NOTIFY_RECOVERY),
                ): bool,
                vol.Optional(
                    CONF_CONNECTION_SERVICES,
                    default=_services_field_default(current, CONF_CONNECTION_SERVICES),
                ): _notify_services_selector(hass),
                vol.Optional(
                    CONF_CONNECTION_TITLE,
                    default=current.get(
                        CONF_CONNECTION_TITLE, DEFAULT_CONNECTION_TITLE
                    ),
                ): str,
                vol.Optional(
                    CONF_CONNECTION_ERROR_DELAY,
                    default=current.get(
                        CONF_CONNECTION_ERROR_DELAY, DEFAULT_CONNECTION_ERROR_DELAY
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=30, max=3600)),
                vol.Optional(
                    CONF_CONNECTION_QUIET_ENABLED,
                    default=current.get(
                        CONF_CONNECTION_QUIET_ENABLED, DEFAULT_QUIET_HOURS_ENABLED
                    ),
                ): bool,
                vol.Optional(
                    CONF_CONNECTION_QUIET_START,
                    default=current.get(
                        CONF_CONNECTION_QUIET_START, DEFAULT_QUIET_HOURS_START
                    ),
                ): selector.TimeSelector(),
                vol.Optional(
                    CONF_CONNECTION_QUIET_END,
                    default=current.get(
                        CONF_CONNECTION_QUIET_END, DEFAULT_QUIET_HOURS_END
                    ),
                ): selector.TimeSelector(),
            }
        ),
        {"collapsed": True},
    )


def _alarm_section(hass: HomeAssistant, current: dict):
    return section(
        vol.Schema(
            {
                vol.Optional(
                    CONF_NOTIFY_ALARMS,
                    default=current.get(CONF_NOTIFY_ALARMS, DEFAULT_NOTIFY_ALARMS),
                ): bool,
                vol.Optional(
                    CONF_ALARM_NOTIFY_RECOVERY,
                    default=_recovery_default(current, CONF_ALARM_NOTIFY_RECOVERY),
                ): bool,
                vol.Optional(
                    CONF_ALARM_SERVICES,
                    default=_services_field_default(current, CONF_ALARM_SERVICES),
                ): _notify_services_selector(hass),
                vol.Optional(
                    CONF_ALARM_TITLE,
                    default=current.get(CONF_ALARM_TITLE, DEFAULT_ALARM_TITLE),
                ): str,
                vol.Optional(
                    CONF_ALARM_DELAY,
                    default=current.get(CONF_ALARM_DELAY, DEFAULT_ALARM_DELAY),
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=3600)),
                vol.Optional(
                    CONF_ALARM_QUIET_ENABLED,
                    default=current.get(
                        CONF_ALARM_QUIET_ENABLED, DEFAULT_QUIET_HOURS_ENABLED
                    ),
                ): bool,
                vol.Optional(
                    CONF_ALARM_QUIET_START,
                    default=current.get(
                        CONF_ALARM_QUIET_START, DEFAULT_QUIET_HOURS_START
                    ),
                ): selector.TimeSelector(),
                vol.Optional(
                    CONF_ALARM_QUIET_END,
                    default=current.get(CONF_ALARM_QUIET_END, DEFAULT_QUIET_HOURS_END),
                ): selector.TimeSelector(),
            }
        ),
        {"collapsed": True},
    )


def _warning_section(hass: HomeAssistant, current: dict):
    return section(
        vol.Schema(
            {
                vol.Optional(
                    CONF_NOTIFY_WARNINGS,
                    default=current.get(CONF_NOTIFY_WARNINGS, DEFAULT_NOTIFY_WARNINGS),
                ): bool,
                vol.Optional(
                    CONF_WARNING_NOTIFY_RECOVERY,
                    default=_recovery_default(current, CONF_WARNING_NOTIFY_RECOVERY),
                ): bool,
                vol.Optional(
                    CONF_WARNING_SERVICES,
                    default=_services_field_default(current, CONF_WARNING_SERVICES),
                ): _notify_services_selector(hass),
                vol.Optional(
                    CONF_WARNING_TITLE,
                    default=current.get(CONF_WARNING_TITLE, DEFAULT_WARNING_TITLE),
                ): str,
                vol.Optional(
                    CONF_WARNING_DELAY,
                    default=current.get(CONF_WARNING_DELAY, DEFAULT_WARNING_DELAY),
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=3600)),
                vol.Optional(
                    CONF_WARNING_QUIET_ENABLED,
                    default=current.get(
                        CONF_WARNING_QUIET_ENABLED, DEFAULT_QUIET_HOURS_ENABLED
                    ),
                ): bool,
                vol.Optional(
                    CONF_WARNING_QUIET_START,
                    default=current.get(
                        CONF_WARNING_QUIET_START, DEFAULT_QUIET_HOURS_START
                    ),
                ): selector.TimeSelector(),
                vol.Optional(
                    CONF_WARNING_QUIET_END,
                    default=current.get(
                        CONF_WARNING_QUIET_END, DEFAULT_QUIET_HOURS_END
                    ),
                ): selector.TimeSelector(),
            }
        ),
        {"collapsed": True},
    )


def _notification_sections(hass: HomeAssistant, current: dict) -> dict:
    """Collapsible sections: shared settings + one per notification category."""
    return {
        vol.Required(SECTION_GENERAL): _general_section(hass, current),
        vol.Required(SECTION_CONNECTION): _connection_section(hass, current),
        vol.Required(SECTION_ALARM): _alarm_section(hass, current),
        vol.Required(SECTION_WARNING): _warning_section(hass, current),
    }


def _flatten_sections(user_input: dict) -> dict:
    """Merge the per-section dicts the form returns back into flat config keys."""
    flat: dict = {}
    for key, value in user_input.items():
        if key in SECTION_KEYS and isinstance(value, dict):
            flat.update(value)
        else:
            flat[key] = value
    # Store each category's mobile services as a comma-separated string.
    for key in (CONF_CONNECTION_SERVICES, CONF_ALARM_SERVICES, CONF_WARNING_SERVICES):
        flat[key] = _normalize_services(flat.get(key))
    return flat


async def _get_serial_ports() -> list[str]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        lambda: [port.device for port in serial.tools.list_ports.comports()],
    )


@callback
def configured_connections(hass: HomeAssistant) -> set[str]:
    """Return already configured connection ids."""
    configured: set[str] = set()
    for entry in hass.config_entries.async_entries(DOMAIN):
        try:
            configured.add(_connection_unique_id(entry.data))
        except KeyError:
            continue
    return configured


class Magna3ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the MAGNA3 config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self) -> None:
        self._data: dict = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> Magna3OptionsFlow:
        return Magna3OptionsFlow()

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            self._data = dict(user_input)
            if self._data[CONF_MODE] == MODE_SERIAL:
                return await self.async_step_serial()
            return await self.async_step_tcp()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Required(
                        CONF_DEVICE_ID, default=DEFAULT_DEVICE_ID
                    ): _device_id_selector(),
                    vol.Required(CONF_MODE, default=MODE_TCP): vol.In(MODES),
                }
            ),
        )

    async def async_step_tcp(self, user_input=None) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            candidate = {**self._data, **user_input}
            host = candidate[CONF_HOST].strip().lower()
            candidate[CONF_HOST] = host

            if not host_valid(host):
                errors[CONF_HOST] = "invalid_host"
            else:
                self._data = candidate
                return await self.async_step_notifications()

        return self.async_show_form(
            step_id="tcp",
            data_schema=vol.Schema(_tcp_schema_fields(self._data)),
            errors=errors,
        )

    async def async_step_serial(self, user_input=None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        serial_ports = await _get_serial_ports()
        default_device = self._data.get(CONF_DEVICE) or (
            serial_ports[0] if serial_ports else ""
        )

        if user_input is not None:
            candidate = {**self._data, **user_input}
            candidate[CONF_BYTESIZE] = DEFAULT_BYTESIZE

            if serial_ports and candidate[CONF_DEVICE] not in serial_ports:
                errors[CONF_DEVICE] = "invalid_serial_port"
            else:
                self._data = candidate
                return await self.async_step_notifications()

        return self.async_show_form(
            step_id="serial",
            data_schema=vol.Schema(
                _serial_schema_fields(self._data, serial_ports, default_device)
            ),
            errors=errors,
        )

    async def async_step_notifications(self, user_input=None) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            flat = _flatten_sections(user_input)
            candidate = {**self._data, **flat}
            unique_id = _connection_unique_id(candidate)
            if unique_id in configured_connections(self.hass):
                errors["base"] = "already_configured"
            else:
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=candidate[CONF_NAME], data=candidate
                )

        return self.async_show_form(
            step_id="notifications",
            data_schema=vol.Schema(_notification_sections(self.hass, self._data)),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input=None) -> ConfigFlowResult:
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if entry is None:
            return self.async_abort(reason="unknown")

        if not self._data:
            self._data = dict(entry.data)

        if user_input is not None:
            self._data.update(user_input)
            if self._data[CONF_MODE] == MODE_SERIAL:
                return await self.async_step_reconfigure_serial()
            return await self.async_step_reconfigure_tcp()

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME, default=self._data.get(CONF_NAME, DEFAULT_NAME)
                    ): str,
                    vol.Required(
                        CONF_DEVICE_ID,
                        default=self._data.get(CONF_DEVICE_ID, DEFAULT_DEVICE_ID),
                    ): _device_id_selector(),
                    vol.Required(
                        CONF_MODE, default=self._data.get(CONF_MODE, MODE_TCP)
                    ): vol.In(MODES),
                }
            ),
        )

    async def async_step_reconfigure_tcp(self, user_input=None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if entry is None:
            return self.async_abort(reason="unknown")

        if user_input is not None:
            merged = {**self._data, **user_input}
            merged[CONF_MODE] = MODE_TCP
            host = merged[CONF_HOST].strip().lower()
            merged[CONF_HOST] = host

            if not host_valid(host):
                errors[CONF_HOST] = "invalid_host"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=_connection_unique_id(merged),
                    data=merged,
                    reason="reconfigure_successful",
                )

        return self.async_show_form(
            step_id="reconfigure_tcp",
            data_schema=vol.Schema(_tcp_schema_fields(self._data)),
            errors=errors,
        )

    async def async_step_reconfigure_serial(self, user_input=None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if entry is None:
            return self.async_abort(reason="unknown")

        serial_ports = await _get_serial_ports()
        default_device = self._data.get(
            CONF_DEVICE, serial_ports[0] if serial_ports else ""
        )

        if user_input is not None:
            merged = {**self._data, **user_input}
            merged[CONF_MODE] = MODE_SERIAL
            merged[CONF_BYTESIZE] = DEFAULT_BYTESIZE

            if serial_ports and merged[CONF_DEVICE] not in serial_ports:
                errors[CONF_DEVICE] = "invalid_serial_port"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=_connection_unique_id(merged),
                    data=merged,
                    reason="reconfigure_successful",
                )

        return self.async_show_form(
            step_id="reconfigure_serial",
            data_schema=vol.Schema(
                _serial_schema_fields(self._data, serial_ports, default_device)
            ),
            errors=errors,
        )


class Magna3OptionsFlow(config_entries.OptionsFlow):
    """Handle the MAGNA3 options flow (notifications + polling)."""

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            flat = _flatten_sections(user_input)
            data = {**self.config_entry.data, **flat}
            self.hass.config_entries.async_update_entry(self.config_entry, data=data)
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        current = self.config_entry.data
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
                **_notification_sections(self.hass, current),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
