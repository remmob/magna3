
[![en](https://img.shields.io/badge/lang-en-red.svg)](README.md)
[![nl](https://img.shields.io/badge/lang-nl-orange.svg)](README.nl.md)

# Grundfos MAGNA3 – Modbus integration for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-41BDF5.svg)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Monitor and control a **Grundfos MAGNA3** circulation pump from Home
Assistant over Modbus — via a **CIM 200** module (Modbus RTU / serial) or a
**CIM 500** module (Modbus TCP). No cloud, no Grundfos GO app required:
everything runs locally, polling the pump directly.

🇳🇱 Nederlandse versie: [README.nl.md](README.nl.md)

> **Disclaimer**: This is an independent, community-built integration. It is not affiliated with, endorsed by, or supported by Grundfos. "Grundfos" and the Grundfos logo are trademarks of their respective owner, used here only to identify compatible hardware. The software is provided as-is (see [LICENSE](LICENSE)); wiring your unit and connecting a gateway is done at your own risk.

---

## Table of contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Control](#control)
- [Settings & notifications](#settings--notifications)
- [Sensors](#sensors)
- [Connection health monitoring](#connection-health-monitoring)
- [Troubleshooting](#troubleshooting)
- [Technical reference](#technical-reference)
- [Contributing](#contributing)

---

## Features

- **Full pump control** — turn the pump on/off, switch control mode
  (constant curve, constant pressure, AUTOADAPT, FLOWLIMIT, …), set the
  setpoint and a maximum flow limit, reset alarms, all from Home Assistant.
- **Rich measurement data** — head, flow, speed, power, energy, temperatures,
  operating hours, number of starts, and more.
- **Local polling only** — talks directly to the CIM module, no internet or
  cloud account needed.
- **Both connection types** — Modbus TCP (CIM 500) *and* Modbus RTU/serial
  (CIM 200), configurable through the UI.
- **Smart connection monitoring** — detects not just a lost Modbus link, but
  also the more subtle case where the CIM module keeps answering with
  *frozen* data because its internal link to the pump itself has dropped.
- **Per-category notifications with quiet hours** — connection errors, alarms and
  warnings each have their own mobile notify services, notification subject, delay and
  quiet-hours window (hold non-urgent mobile alerts overnight), as persistent and/or
  push notifications.
- **Sensible defaults** — diagnostic and rarely-needed sensors are disabled
  by default so your entity list stays clean; enable them per entity
  whenever you need them.

## Requirements

- Home Assistant with the custom integration installed (see below).
- A Grundfos MAGNA3 pump fitted with a **CIM 200** (RS-485/Modbus RTU) or
  **CIM 500** (Modbus TCP) communication module.
- Network access (TCP) or a serial connection (RTU/USB adapter) from your
  Home Assistant host to the CIM module. A CIM 200 can also be reached over
  the network via a Modbus RTU-to-TCP/IP gateway — see the note under
  [Configuration](#configuration).
- Python dependencies (installed automatically): `pymodbus>=3.6.9`,
  `pyserial>=3.5`.

## Installation

> ℹ️ Not in the HACS default store yet — install via custom repository or manually for now.

### HACS (custom repository)

1. Open **HACS** in Home Assistant.
2. Click the three-dot menu (⋮) in the top right corner.
3. Select **Custom repositories**.
4. Add this repository URL: `https://github.com/remmob/magna3`.
5. Set the category to **Integration** and click **Add**.
6. Search for **Grundfos MAGNA3** and download it.
7. **Restart Home Assistant**.

See the [official HACS documentation](https://hacs.xyz/docs/faq/custom_repositories/) for more details.

### Manual

1. Download or copy the `custom_components/magna3` folder from this repository into
   your Home Assistant `config/custom_components/` directory.
2. **Restart Home Assistant**.

## Configuration

Configuration is done entirely through the UI — no YAML required.

**Settings → Devices & services → Add integration → Grundfos MAGNA3**

The setup wizard walks through a few steps:

1. **Name & connection type** — give the pump a name, set the Modbus unit
   ID (slave address, 1–247) of the CIM module, and choose **TCP** or
   **Serial**.
2. **Connection details**
   | Mode | Fields |
   |------|--------|
   | TCP (CIM 500) | Host, port (default `502`), scan interval |
   | Serial (CIM 200) | Serial port, baud rate, parity, stop bits, scan interval |

   The CIM 200 factory default is **even parity, 1 stop bit**; it also
   supports *no parity, 2 stop bits* if you've reconfigured it that way.

   > **Using a Modbus RTU-to-TCP/IP gateway with a CIM 200?** Pick **TCP**
   > in the wizard instead of Serial, and point it at the gateway's IP
   > address and port. The gateway handles the RS-485/RTU side towards the
   > CIM 200; Home Assistant only ever talks Modbus TCP to the gateway. This
   > also lets you place the pump anywhere on your network instead of
   > needing a direct serial/USB connection to the HA host.
3. **Notifications** — optionally enable alarm/warning/connection
   notifications and where they should go (see
   [Settings & notifications](#settings--notifications)).

Multiple pumps? Just add the integration again — each connection (host+port
or serial port) can only be added once, so Home Assistant will warn you if
you try to add the same pump twice.

All of the above can be changed later via **Configure** on the integration
tile (reconfigure connection) or the entry's **Options** (notifications and
scan interval).

## Control

The integration exposes a set of entities you use to actually operate the
pump:

| Entity | Type | What it does |
|--------|------|---------------|
| **Remote control** | switch | Master switch: the pump only accepts Modbus commands while this is on. |
| **Pump** | switch | Turns the pump on/off. |
| **Regelmodus** / **Control mode** | select | Chooses how the pump regulates itself: constant curve, constant pressure, proportional pressure, AUTOADAPT, FLOWLIMIT, and more. |
| **Bedrijfsmodus** / **Operating mode** | select | Normal (setpoint-controlled), minimum speed, or maximum speed. |
| **Setpoint** | number (slider) | Target value for the active control mode, 0–100 %, bounded by the pump's own configured setpoint range. |
| **Flow limit** | switch | Enables/disables the maximum flow limit. |
| **Maximum flow limit** | number | The flow ceiling (m³/h) used when the flow limit switch is on. |
| **Reset alarm** | button | Clears the current alarm/warning on the pump. |

### Why "Remote control" matters

Grundfos pumps only accept Modbus commands while **remote (Modbus) control**
is active on the pump itself. If you flip the physical R100 remote or the
pump's local buttons, or if the installer left it in local mode, Home
Assistant's write attempts will otherwise be silently ignored by the pump.

To make this predictable, every control entity in this integration
**automatically turns on Remote control** before writing anything. If the
pump refuses to enter remote mode (e.g. its keypad is locked, or it has
been *forced to local* — see the *Forced to local* diagnostic sensor), you
get a clear Home Assistant error instead of a command that silently does
nothing.

## Settings & notifications

Notifications live in **collapsible sections** under the integration's
**Configure → Options**, so connection errors, alarms and warnings can each be tuned
independently.

**General**

| Setting | Description |
|---------|--------------|
| Scan interval | How often the pump is polled (default 30 s). |
| Persistent notifications | Also show notifications in the Home Assistant notification panel. |

**Connection errors**, **Alarms** and **Warnings** each have their own section with:

| Setting | Description |
|---------|--------------|
| Notify on … | Enable notifications for this category. |
| Notify on recovery | Also notify once this category clears (the alarm/warning is gone, or the connection is restored). |
| Mobile notify services | Which `notify.*` services (e.g. your phone's `mobile_app_*`) receive **this** category — so e.g. a filter warning can reach your partner while a connection error does not. |
| Notification subject | The title used for this category's notifications — handy to tell multiple pumps apart. |
| Delay (seconds) | How long the condition must persist before notifying, so a code or blip that clears itself immediately doesn't notify. |
| Quiet hours | Optionally hold **mobile** notifications during a set period (e.g. at night) and deliver them once it ends — each category has its own window. Persistent notifications are never held. |

Connection-error notifications fire both when the Modbus link is lost *and* when the CIM
module stops hearing from the pump (GENIbus link down).

## Sensors

All numeric process values are exposed as sensors, correctly scaled and
unit-tagged so they work out of the box with the Energy dashboard and
long-term statistics.

**Enabled by default:** Head, Flow, Relative performance, Speed, Actual
setpoint, Motor current, Liquid temperature, Electronics temperature,
Power, Energy, Operating hours, Number of starts.

**Diagnostic / disabled by default** (enable per-entity if you need them):
Frequency, DC-link voltage, Process feedback, Remote pressure 1,
Specific energy consumption, Remote temperature 2, Differential pressure,
Powered time, Heat energy, Heat power, Pumped volume.

Plus a set of binary sensors for pump state: **Running**, **Fault**,
**Warning**, **At power limit**, **At maximum/minimum speed**,
**Forced to local**, and two connection-health sensors (see below).

For the full register-level mapping (which is handy if you're debugging or
extending the integration), see [Technical reference](#technical-reference).

## Connection health monitoring

Two different things can go wrong, and this integration distinguishes
between them:

1. **CIM connection** *(binary_sensor)* — is Home Assistant able to talk to
   the CIM module over Modbus at all?
2. **Pump communication** *(binary_sensor)* — is the CIM module itself still
   hearing from the pump over its internal GENIbus link?

The second one exists because the CIM module keeps serving its **last known
values** over Modbus even when its internal link to the pump has dropped —
the data still looks valid, it's just frozen. The integration detects this
by watching the pump's GENIbus receive counter; if it hasn't moved for
3 consecutive polls, *Pump communication* switches to unavailable and the
sensor **Connection status** reports `No pump data`.

## Troubleshooting

- **Writing a setpoint / switching modes does nothing** — check that
  *Remote control* is on and that *Forced to local* is off. If the pump's
  keypad is locked to local control, Modbus commands are ignored by design.
- **A sensor shows "unavailable"** — the pump reports `0xFFFF` for
  registers it doesn't support for your specific model/configuration; the
  integration treats that as "no value" rather than a bogus reading.
- **"Pump communication" is off but "CIM connection" is on** — the Modbus
  link to the CIM module works, but the CIM has lost its internal link to
  the pump. Check the pump's power and the cable between pump and CIM
  module.
- **Serial (CIM 200) connection fails** — double-check baud rate and
  parity/stop-bit settings match the CIM 200's configuration (factory
  default: 19200 baud, even parity, 1 stop bit).
- **Alarm codes** — the sensor **Alarm** / **Warning** shows a human
  readable description (e.g. `Dry running`, `Overtemperature`) alongside the
  raw code; `0` always means "OK".

## Technical reference

<details>
<summary>Register map, bit layouts and scaling details (for developers)</summary>

This section documents the underlying Modbus register mapping, following
the Grundfos documentation numbering (1-based) from the *"Modbus for
Grundfos pumps"* functional profile. Documentation register `X` is
addressed as `X − 1` on the wire; the hub subtracts 1 automatically on every
read/write. All registers are holding registers (function code 03 read /
06 write); `0xFFFF` means *register not available* and is treated as
`None`. 32-bit values are split across two consecutive registers
(HI, HI+1), combined as `(HI << 16) | LO`.

For efficiency, registers are read in contiguous blocks. A block may
include addresses that aren't decoded into an entity — that's read
efficiency, not a missing feature.

| Block | Registers | Frequency | Actually used |
|-------|-----------|-----------|----------------|
| Static | `00023–00024` | once at startup | `00023–00024` (CIM version, Modbus address) |
| Static | `00030–00036` | once at startup | `00030–00032`, `00034–00035` (unit type, software version) |
| Static | `00212–00216` | once at startup | `00212`, `00215–00216` (nominal frequency, setpoint range) |
| Cyclic | `00021–00028` | every poll | only `00027–00028` (GENIbus RX counter) |
| Cyclic | `00101–00108` | every poll | `00101–00104`, `00106` (control block) |
| Cyclic | `00201–00208` | every poll | `00201–00206` (status, modes, alarm/warning) |
| Cyclic | `00301–00358` | every poll | see measurement table below |

#### Control registers (writable)

| Register | Name | Entity | Scale / meaning |
|----------|------|--------|--------------------|
| `00101` | ControlBits | switches + *Reset alarm* button | bitfield, see below |
| `00102` | ControlMode | select *Control mode* | enum, `CONTROL_MODES` |
| `00103` | OperationMode | select *Operating mode* | enum, `OPERATION_MODES` |
| `00104` | Setpoint | number *Setpoint* | 0.01 % (0–100 % → 0–10000) |
| `00106` | MaxFlowLimit | number *Maximum flow limit* | 0.01 m³/h on write |

**ControlBits (`00101`)** — read-modify-write bitfield, each bit set/cleared
independently:

| Bit | Name | Entity |
|-----|------|--------|
| 0 | RemoteAccess | switch *Remote control* |
| 1 | OnOff | switch *Pump* |
| 2 | ResetAlarm | button *Reset alarm* (rising edge) |
| 5 | EnableMaxFlowLimit | switch *Flow limit* |

#### Status registers (read-only)

| Register | Name | Entity | Meaning |
|----------|------|--------|---------|
| `00201` | StatusBits | see bit table below | bitfield |
| `00202` | ProcessFeedback | sensor *Process feedback* (diagnostic) | process feedback in %, scale 0.01 |
| `00203` | ActualControlMode | select *Control mode* (readback) | actually active control mode |
| `00204` | ActualOperationMode | select *Operating mode* (readback) | actually active operating mode |
| `00205` | AlarmCode | sensor *Alarm* | current alarm code (`0` = OK) |
| `00206` | WarningCode | sensor *Warning* | current warning code |

**StatusBits (`00201`)**:

| Bit | Name | Entity | Meaning |
|-----|------|--------|---------|
| 2 | MaxFlowLimitEnabled | switch *Flow limit* (state) | max. flow limit active |
| 5 | AtMaxPower | binary_sensor *At power limit* (disabled by default) | pump at maximum power |
| 6 | Rotation | binary_sensor *Running* | pump is running |
| 8 | AccessMode | switch *Remote control* (state) | Modbus control active |
| 9 | OnOff | switch *Pump* (state) | pump on/off status |
| 10 | Fault | binary_sensor *Fault* | alarm active |
| 11 | Warning | binary_sensor *Warning* | warning active |
| 12 | ForcedToLocal | binary_sensor *Forced to local* (disabled by default) | pump forced to local control |
| 13 | AtMaxSpeed | binary_sensor *At maximum speed* (disabled by default) | pump at max speed |
| 15 | AtMinSpeed | binary_sensor *At minimum speed* (disabled by default) | pump at min speed |

#### Measurement registers (read-only, `00301`–`00358`)

Temperatures arrive as kelvin × 100 and are converted to °C
(`offset = −273.15`).

| Register | Quantity | Unit | Scale | Entity |
|----------|----------|------|-------|--------|
| `00301` | Head | bar | 0.001 | sensor *Head* |
| `00302` | Flow | m³/h | 0.1 | sensor *Flow* |
| `00303` | Relative performance | % | 0.01 | sensor *Relative performance* |
| `00304` | Speed | rpm | 1 | sensor *Speed* |
| `00305` | Frequency | Hz | 0.1 | sensor *Frequency* (disabled by default) |
| `00308` | Actual setpoint | % | 0.01 | sensor *Actual setpoint* |
| `00309` | Motor current | A | 0.1 | sensor *Motor current* (diagnostic) |
| `00310` | DC-link voltage | V | 0.1 | sensor *DC-link voltage* (disabled by default) |
| `00312`+`00313` | Power | W | 1 | sensor *Power* (32-bit) |
| `00316` | Remote pressure 1 | bar | 0.001 | sensor *Remote pressure 1* (disabled by default) |
| `00321` | Electronics temperature | °C | 0.01 (K) | sensor *Electronics temperature* (diagnostic) |
| `00322` | Liquid temperature | °C | 0.01 (K) | sensor *Liquid temperature* |
| `00326` | Specific energy consumption | Wh/m³ | 1 | sensor *Specific energy consumption* (disabled by default) |
| `00327`+`00328` | Operating hours | h | 1 | sensor *Operating time* (32-bit, diagnostic) |
| `00329`+`00330` | Powered hours | h | 1 | sensor *Powered time* (32-bit, disabled by default) |
| `00332`+`00333` | Energy consumption | kWh | 1 | sensor *Energy* (32-bit, total) |
| `00334`+`00335` | Number of starts | – | 1 | sensor *Number of starts* (32-bit, diagnostic) |
| `00337` | Remote temperature 2 | °C | 0.01 (K) | sensor *Remote temperature 2* (disabled by default) |
| `00338` | Actual user setpoint | % | 0.01 | number *Setpoint* (readback) |
| `00339` | Differential pressure | bar | 0.001 | sensor *Differential pressure* (disabled by default) |
| `00345` | Actual max. flow limit | m³/h | 0.01 | number *Maximum flow limit* (readback) |
| `00352`+`00353` | Heat energy | kWh | 1 | sensor *Heat energy* (32-bit, disabled by default) |
| `00354`+`00355` | Heat power | W | 1 | sensor *Heat power* (32-bit, disabled by default) |
| `00357`+`00358` | Pumped volume | m³ | 0.01 | sensor *Pumped volume* (32-bit, disabled by default) |

> **Flow limit scale:** both the write register `00106` and the readback register
> `00345` use scale 0.01 m³/h (`number.py`).

#### Static identification/configuration registers

Read once at startup/reload (`_read_static_data`); these back device info
and the *Setpoint* slider bounds, and have no entity of their own.

| Register | Meaning | Processing |
|----------|---------|------------|
| `00023` | CIM version number | raw |
| `00024` | Actual Modbus address | raw |
| `00030` | Unit family | raw |
| `00031` | Unit type | raw |
| `00032` | Unit version | raw |
| `00034`+`00035` | Product software version | BCD, formatted as `x.y.z` |
| `00212` | Nominal frequency | scale 0.1 Hz |
| `00215` | Setpoint range minimum | %, scale 0.01 — bounds number *Setpoint* |
| `00216` | Setpoint range maximum | %, scale 0.01 — bounds number *Setpoint* |

#### Derived entities (no register of their own)

| Entity | Source |
|--------|--------|
| binary_sensor *CIM connection* | Modbus link HA ↔ CIM module (`connection_status == OK`) |
| sensor *Connection status* | `OK` / `Partial` / `Failed` / `No pump data` (diagnostic) |
| binary_sensor *Pump communication* | GENIbus link CIM ↔ pump, derived from RX counter `00027`+`00028` |

#### Source files

| File | Contents |
|------|----------|
| [`const.py`](const.py) | register numbers, read blocks, scale/enum definitions |
| [`hub.py`](hub.py) | Modbus communication, poll coordinator, `X−1` addressing |
| [`sensor.py`](sensor.py) / [`binary_sensor.py`](binary_sensor.py) | measurement and status sensors |
| [`number.py`](number.py) | setpoint and maximum flow limit (write) |
| [`select.py`](select.py) | control mode and operating mode (write) |
| [`switch.py`](switch.py) | remote control, pump on/off, flow limit (ControlBits) |
| [`button.py`](button.py) | reset alarm (ControlBits bit 2) |

</details>

## Contributing

Issues and pull requests are welcome at
<https://github.com/remmob/magna3>. If you're reporting a bug,
please include your CIM module type (200/500), connection mode, and the
relevant Home Assistant log lines.
