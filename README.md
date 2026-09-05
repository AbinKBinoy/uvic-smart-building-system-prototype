# UVic Smart Building System Prototype

A zone-level **Smart Building Management System (BMS)** prototype built on a
Raspberry Pi Pico W. It integrates occupancy detection, ambient light
sensing, and temperature monitoring to automate lighting and HVAC control,
with a real-time web dashboard for monitoring and manual override.

Built for **ENGR 120 — Design & Communication II**, University of Victoria.

![Status](https://img.shields.io/badge/status-prototype-blue)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi%20Pico%20W-green)
![Language](https://img.shields.io/badge/language-MicroPython-yellow)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Hardware](#hardware)
- [Circuit Diagram](#circuit-diagram)
- [Software Architecture](#software-architecture)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Calibration Notes](#calibration-notes)
- [Known Limitations](#known-limitations)
- [Future Improvements](#future-improvements)
- [License](#license)

---

## Overview

Buildings waste significant energy heating, cooling, and lighting rooms
that are unoccupied. This project prototypes a low-cost, single-zone
Building Management System that:

- Detects occupancy with a PIR motion sensor
- Reads ambient light with a photoresistor (LDR)
- Reads temperature with an NTC thermistor
- Automatically controls lighting and HVAC based on occupancy state
- Uses **two different temperature ranges** depending on occupancy:
  - **Comfort range** (occupied) — optimized for human comfort
  - **Preservation range** (unoccupied) — wider range that still protects
    the room from damage (mold, moisture, material stress) while saving
    energy
- Hosts a **self-contained web dashboard** directly on the Pico W (no
  internet or external server required) for live monitoring and manual
  override

Since the project's Technology Readiness Level (TRL) is below 4, LEDs are
used to represent real-world actuators (lighting fixtures, heating, and
cooling systems).

---

## Features

- ✅ PIR-based occupancy detection with debounce logic
- ✅ Ambient light sensing with configurable threshold
- ✅ Temperature sensing via NTC thermistor using the Steinhart–Hart Beta
  equation
- ✅ Dual-mode HVAC control (Comfort vs. Preservation thresholds)
- ✅ Self-hosted Wi-Fi Access Point — no router or internet needed
- ✅ Real-time web dashboard (updates every 2 seconds via AJAX polling)
- ✅ Manual override controls for lighting and HVAC from the browser
- ✅ Live-adjustable temperature thresholds from the UI
- ✅ Temperature history chart (last ~2 minutes of readings)
- ✅ Event log with timestamps (mode changes, overrides, threshold edits)
- ✅ Responsive layout — full-width on desktop, single column on mobile

---

## Hardware

| Component                  | Function              | Pico W Pin      |
|-----------------------------|------------------------|-----------------|
| PIR Motion Sensor            | Occupancy detection    | GP28 (digital in) |
| Photoresistor (LDR)          | Ambient light sensing  | GP27 / ADC1     |
| NTC Thermistor (10 kΩ)       | Temperature sensing    | GP26 / ADC0     |
| White LED (+ 100 Ω resistor) | Lighting actuator      | GP18 (digital out) |
| Red LED (+ 100 Ω resistor)   | Heating actuator       | GP16 (digital out) |
| Green LED (+ 100 Ω resistor) | Cooling actuator       | GP17 (digital out) |

**Voltage dividers:**
- Thermistor: 10 kΩ fixed resistor + 10 kΩ NTC thermistor
- LDR: 10 kΩ fixed resistor + photoresistor

See [`docs/circuit-notes.md`](docs/circuit-notes.md) for wiring orientation
and common mistakes.

---

## Circuit Diagram

See [`docs/circuit-notes.md`](docs/circuit-notes.md) for the full block
diagram and voltage divider orientation notes (including the "reversed
thermistor" and "reversed LDR" issues we ran into — see
[Known Limitations](#known-limitations)).

---

## Software Architecture

Written in **MicroPython**, running entirely on the Pico W. No external
backend or database — the microcontroller is simultaneously the sensor
controller, the Wi-Fi access point, and the web server.

```
┌─────────────────────────────────────────────┐
│              Raspberry Pi Pico W             │
│                                               │
│  ┌───────────┐   ┌──────────────┐            │
│  │  Sensors  │──▶│ Control Logic │──▶ LEDs    │
│  └───────────┘   └──────────────┘            │
│         │                │                   │
│         └────────┬───────┘                   │
│                   ▼                          │
│         ┌───────────────────┐                │
│         │  Wi-Fi AP + Socket │               │
│         │   Server (port 80) │               │
│         └─────────┬──────────┘               │
└───────────────────┼──────────────────────────┘
                     │  HTTP (AJAX polling every 2s)
                     ▼
           ┌───────────────────┐
           │   Browser (phone   │
           │   or laptop)       │
           └───────────────────┘
```

**Two HTTP endpoints:**

| Endpoint | Method | Returns                                   |
|----------|--------|--------------------------------------------|
| `/`      | GET    | Full HTML dashboard (built once, ~4 KB)    |
| `/data`  | GET    | Pipe-separated live sensor string (~100 B) |

Commands (button clicks, threshold changes) are sent as query parameters
on `GET /`, e.g. `GET /?cmd=hvac_heating` or
`GET /?set_cl=20.0&set_ch=24.0&set_pl=15.0&set_ph=28.0`.

See [`docs/architecture.md`](docs/architecture.md) for the full request/
response flow, data format, and control logic explanation.

---

## Getting Started

### Requirements
- Raspberry Pi Pico **W** (must be the W variant — Wi-Fi required)
- [Thonny IDE](https://thonny.org/)
- MicroPython firmware built for **Pico W** (not the plain Pico)
  → [Download here](https://micropython.org/download/RPI_PICO_W/)

### Flashing the firmware
1. Unplug the Pico W
2. Hold the **BOOTSEL** button and plug it into USB
3. Release BOOTSEL — it appears as a USB drive named `RPI-RP2`
4. Drag the downloaded `.uf2` file onto that drive
5. The board reboots automatically running MicroPython

### Uploading the code
1. Open [`src/main.py`](src/main.py) in Thonny
2. Make sure the interpreter (bottom-right of Thonny) says
   **MicroPython (Raspberry Pi Pico W)**
3. Click **Run** → when prompted, save to **Raspberry Pi Pico** as
   `main.py` (so it auto-runs on boot)

### Wiring
Follow the pin table in [Hardware](#hardware) and the notes in
[`docs/circuit-notes.md`](docs/circuit-notes.md).

---

## Usage

1. Power the Pico W (USB or battery pack)
2. Wait ~15 seconds for PIR sensor calibration (printed to serial console)
3. On your phone or laptop, connect to the Wi-Fi network:
   - **SSID:** `BMS_UVic`
   - **Password:** `engr120bms`
4. Open a browser and go to the IP address printed in the Thonny console
   (typically `192.168.4.1`)
5. The dashboard loads and begins updating every 2 seconds

**Try it out:**
- Wave your hand in front of the PIR sensor → occupancy badge changes
- Cover the LDR → white LED turns on (if occupied)
- Warm/cool the thermistor → red/green LED responds based on active
  threshold range
- Use the on-screen buttons to manually override lighting/HVAC
- Adjust the +/- threshold controls and watch the system respond live

---

## Project Structure

```
uvic-smart-building-system-prototype/
├── README.md                 ← you are here
├── LICENSE
├── src/
│   └── main.py                ← final production code (sensors + Wi-Fi + dashboard)
├── tests/
│   ├── test_sensors.py        ← sensor/LED test script, no Wi-Fi (hardware bring-up)
│   └── web_test.py            ← minimal web server test (network bring-up)
└── docs/
    ├── architecture.md        ← backend/frontend data flow, API details
    ├── circuit-notes.md       ← wiring, voltage dividers, calibration
    └── flowchart.md           ← control logic description
```

**Why two test files exist:** during development, sensors and the web
server were debugged independently before integrating everything into
`main.py`. `test_sensors.py` verifies hardware wiring/logic with plain
serial output (no networking). `web_test.py` verifies the Wi-Fi/socket
server works before adding sensor logic on top. This isolation made it
much faster to track down bugs (see `docs/architecture.md` for details on
issues found this way).

---

## Calibration Notes

- **`LIGHT_THRESHOLD = 40000`** — tune this for your specific LDR/resistor
  pairing. Watch the raw ADC value in the serial monitor while covering/
  uncovering the sensor, then set the threshold roughly halfway between
  the bright and dark readings.
- **Thermistor constants** (`THERMISTOR_R0`, `THERMISTOR_B`) come from the
  datasheet for a 10 kΩ NTC thermistor. If using a different thermistor,
  update these values.
- **Voltage divider orientation matters.** If your temperature or light
  readings behave backwards (e.g. temperature drops when heated), your
  sensor and fixed resistor are likely swapped — see
  [`docs/circuit-notes.md`](docs/circuit-notes.md).

---

## Known Limitations

- LEDs represent actuators (lighting/HVAC) rather than controlling real
  hardware, since the project TRL is below 4 and real actuators require
  higher-voltage/current drivers and protection circuitry.
- Event log and temperature history are stored in RAM only — they reset
  on reboot (no persistent storage/RTC).
- Single-zone only — one Pico W monitors one room. See
  [Future Improvements](#future-improvements) for multi-room scaling.
- Wi-Fi Access Point mode means the dashboard is only reachable by devices
  connected directly to the Pico's network (no internet access required
  or provided).

---

## Future Improvements

- Swap individual light/temp sensors for a combined temperature+humidity
  module (e.g. DHT22) — humidity matters for mold/moisture prevention in
  preservation mode
- Add a real-time clock (RTC) module for real timestamps in the event log
- Replace indicator LEDs with actual relay-driven HVAC/lighting hardware
- Move to a three-tier architecture (Pico ↔ backend server ↔ frontend
  app) to support multiple rooms/zones reporting to one dashboard —
  see `docs/architecture.md` for a comparison of this approach
- Persist temperature history and event logs to flash storage or an
  external database
- Add scheduling (different comfort ranges by time of day)

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Author

**AbinKBinoy**
First-year Software Engineering student, University of Victoria
Built for ENGR 120 — Design & Communication II
