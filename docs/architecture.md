# Architecture

This document explains how the Pico W serves both the sensor control logic
and the web dashboard from a single device, and how data flows between the
hardware and the browser.

## Table of Contents
- [High-level design](#high-level-design)
- [Why a single device instead of a backend server](#why-a-single-device-instead-of-a-backend-server)
- [HTTP endpoints](#http-endpoints)
- [Data format](#data-format)
- [Request/response flow](#requestresponse-flow)
- [Control logic](#control-logic)
- [Alternative architecture (three-tier)](#alternative-architecture-three-tier)

---

## High-level design

The Pico W runs a single `while True` loop that, on every iteration:

1. Reads all sensors (motion, temperature, light)
2. Updates occupancy state (with debounce)
3. Runs lighting and HVAC control logic (respecting manual overrides)
4. Checks for an incoming web request (0.5s timeout) and responds if present
5. Prints status to the serial console every 2 seconds

This is a deliberate design choice for a **self-contained prototype** —
there is no separate backend server, database, or router. The Pico W:
- Broadcasts its own Wi-Fi network (Access Point mode)
- Runs a TCP socket server on port 80 (standard HTTP port)
- Serves both the dashboard page and its own data API

## Why a single device instead of a backend server

Some IoT projects use a three-tier design: microcontroller → backend
server (Flask/Node) → frontend app (React). That approach is more scalable
(multiple devices reporting to one dashboard, persistent storage, more
powerful UI frameworks) but requires additional infrastructure to be
running at all times.

For a single-zone prototype, a two-tier design (browser ↔ Pico W directly)
was chosen because:
- No additional hardware/server needed — plug in the Pico and it works
- No dependency on an existing Wi-Fi network or internet connection
- Simpler to demonstrate and debug for a course project
- Demonstrates the full IoT loop (sensor → decision → actuator → UI) in
  one device

See [Alternative architecture](#alternative-architecture-three-tier) below
for how this could be extended for a multi-room deployment.

## HTTP endpoints

The Pico exposes exactly two GET endpoints:

| Endpoint | Purpose                              | Typical size |
|----------|----------------------------------------|--------------|
| `GET /`  | Serves the full HTML/CSS/JS dashboard | ~4 KB        |
| `GET /data` | Serves current sensor/state data as a compact string | ~100 bytes |

Commands are **not** separate endpoints — they are passed as query
parameters on `GET /`:

```
GET /?cmd=hvac_heating
GET /?cmd=light_on
GET /?set_cl=20.0&set_ch=24.0&set_pl=15.0&set_ph=28.0
```

The Pico's request handler (`handle_request()` in `main.py`) inspects the
raw request string for these substrings, updates global state accordingly,
then determines whether to respond with the full page or just the data
string (based on whether the path was `/data`).

This keeps the code simple — one socket, one accept loop, one parser
function — appropriate for the Pico's limited RAM (264 KB).

## Data format

The `/data` endpoint returns a single pipe-separated string:

```
temp|lightStatus|lightRaw|motion|hvacStatus|lightingStatus|lightOverride|hvacOverride|comfortLow|comfortHigh|preserveLow|preserveHigh|tempHistory|eventLog
```

Example:
```
22.4|Dark|48230|1|Off|On|auto|auto|20.0|24.0|15.0|28.0|22.1,22.3,22.4|0m15s System starting,0m5s PIR calibrated
```

| Index | Field | Example |
|-------|-------|---------|
| 0 | Temperature (°C) | `22.4` |
| 1 | Light status | `Dark` / `Bright` |
| 2 | Raw light ADC value | `48230` |
| 3 | Motion (1/0) | `1` |
| 4 | HVAC status | `Heating` / `Cooling` / `Off` |
| 5 | Lighting status | `On` / `Off` |
| 6 | Light override mode | `auto` / `on` / `off` |
| 7 | HVAC override mode | `auto` / `heating` / `cooling` / `off` |
| 8 | Comfort low (°C) | `20.0` |
| 9 | Comfort high (°C) | `24.0` |
| 10 | Preservation low (°C) | `15.0` |
| 11 | Preservation high (°C) | `28.0` |
| 12 | Temperature history (comma-separated) | `22.1,22.3,22.4` |
| 13 | Event log (comma-separated) | `0m15s System starting,...` |

A pipe-separated string (rather than JSON) was used to minimize response
size and avoid needing a JSON encoder on the microcontroller.

## Request/response flow

### Loading the dashboard (once, on page load)

```
Browser                          Pico W
   │  GET /                         │
   │ ───────────────────────────▶  │
   │                                │  build HTML (already built at startup)
   │                                │  send headers + Content-Length
   │  ◀─────────────────────────── │  send HTML in 1024-byte chunks
   │  renders dashboard             │
```

The `Content-Length` header is essential — without it, browsers wait
indefinitely for more data because they don't know when the response is
complete. HTML is sent in 1024-byte chunks rather than all at once because
sending large buffers directly can be unreliable on the Pico's limited
memory.

### Live updates (every 2 seconds, via JavaScript `setInterval`)

```
Browser                          Pico W
   │  GET /data                     │
   │ ───────────────────────────▶  │
   │                                │  build ~100-byte data string
   │  ◀─────────────────────────── │  send it
   │  split by "|", update DOM      │
```

### Sending a command (button click)

```
Browser                          Pico W
   │  GET /?cmd=hvac_heating        │
   │ ───────────────────────────▶  │
   │                                │  set hvac_override = "heating"
   │                                │  log event
   │                                │  turn on red LED (next loop cycle)
   │  ◀─────────────────────────── │  respond with current data
   │  poll() re-runs, UI updates    │
```

## Control logic

```
Read sensors
     │
     ▼
Motion detected? ──Yes──▶ Occupied = True (reset debounce timer)
     │No
     ▼
Debounce timer expired? ──Yes──▶ Occupied = False
     │No
     ▼
(state unchanged)

Lighting:
  If light_override == "on"/"off" → use override
  Else if Occupied AND Dark → LED on
  Else → LED off

HVAC:
  If hvac_override != "auto" → use override
  Else:
    range = Comfort (20-24°C) if Occupied else Preservation (15-28°C)
    If temp < range.low  → Heating (red LED)
    If temp > range.high → Cooling (green LED)
    Else                 → Off
```

Manual overrides always take priority over automatic sensor-based logic.
Setting an override back to `"auto"` returns control to the sensors.

## Alternative architecture (three-tier)

For comparison, a more scalable design (useful for multi-room deployments)
separates the system into three tiers:

```
Pico W (sensors only)  ⇄  Backend server (Flask/FastAPI)  ⇄  Frontend (React)
```

- The Pico exposes simple JSON endpoints (e.g. `GET /device/status`,
  `POST /api/command`) and joins an existing Wi-Fi network (station mode)
  rather than creating its own.
- A backend server (running on a separate machine) polls each Pico
  periodically, caches the latest readings, and exposes its own API for
  the frontend. It can also persist history to a real database.
- A frontend framework (e.g. React) polls the backend — never the Pico
  directly — and renders the UI.

Trade-offs versus this project's two-tier design:

| | Two-tier (this project) | Three-tier |
|---|---|---|
| Extra infrastructure needed | None | Backend server must always be running |
| Works without existing Wi-Fi | Yes (creates its own AP) | No (needs a shared network) |
| Scales to multiple rooms | No (one Pico = one dashboard) | Yes |
| Persistent history | No (RAM only) | Yes (database) |
| Complexity | Low | Higher |

This project intentionally uses the two-tier design because it best suits
a single-zone, self-contained course prototype. The three-tier design is
listed as a future improvement in the main README.
