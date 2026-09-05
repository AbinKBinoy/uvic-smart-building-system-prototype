# Control Logic Flowchart

This describes the decision logic implemented in the main control loop of
`src/main.py`. For the rendered diagram versions used in the project
report, see the presentation materials — this file documents the same
logic in text/pseudocode form for reference alongside the code.

## Main Loop (runs continuously, ~10 times/second)

```
START
  │
  ▼
Initialize GPIO pins, ADC channels
  │
  ▼
Turn off all LEDs
  │
  ▼
Wait 15s for PIR sensor calibration
  │
  ▼
Start Wi-Fi Access Point (SSID: BMS_UVic)
  │
  ▼
Start TCP socket server (port 80, 0.5s timeout)
  │
  ▼
┌─────────────── LOOP START ───────────────┐
│                                            │
│  Read PIR sensor (motion)                 │
│  Read thermistor → convert to °C          │
│  Read LDR → classify Dark/Bright          │
│                                            │
│  ┌─────────────────────────────────┐      │
│  │ Motion == 1?                    │      │
│  │   Yes → occupied = True         │      │
│  │         reset debounce timer    │      │
│  │   No  → if debounce expired:    │      │
│  │           occupied = False      │      │
│  └─────────────────────────────────┘      │
│                                            │
│  ┌─────── Lighting control ────────┐      │
│  │ If light_override != auto:      │      │
│  │     use override (on/off)       │      │
│  │ Else:                           │      │
│  │     If occupied AND Dark:       │      │
│  │         White LED ON            │      │
│  │     Else:                       │      │
│  │         White LED OFF           │      │
│  └──────────────────────────────────┘      │
│                                            │
│  ┌─────── HVAC control ────────────┐      │
│  │ If hvac_override != auto:       │      │
│  │     use override                │      │
│  │     (heating/cooling/off)       │      │
│  │ Else:                           │      │
│  │   range = Comfort if occupied   │      │
│  │           else Preservation     │      │
│  │   If temp < range.low:          │      │
│  │       Red LED ON (Heating)      │      │
│  │   Elif temp > range.high:       │      │
│  │       Green LED ON (Cooling)    │      │
│  │   Else:                         │      │
│  │       Both OFF                  │      │
│  └──────────────────────────────────┘      │
│                                            │
│  Every 4s: append temp to history[]        │
│  (max 30 entries, oldest dropped)          │
│                                            │
│  ┌─────── Web request? (0.5s check) ┐     │
│  │ If GET /:                        │     │
│  │     parse any ?cmd= or ?set_*=   │     │
│  │     params, update state         │     │
│  │     send full HTML dashboard     │     │
│  │ If GET /data:                    │     │
│  │     send pipe-separated sensor   │     │
│  │     string                       │     │
│  │ Else (timeout, no request):      │     │
│  │     continue                     │     │
│  └────────────────────────────────────┘   │
│                                            │
│  Every 2s: print status to serial console  │
│                                            │
└──────────────── LOOP BACK ────────────────┘
```

## Occupied vs. Unoccupied Threshold Ranges

| Mode | Trigger | Temperature range | Purpose |
|------|---------|---------------------|---------|
| **Comfort** | Motion detected | 20.0°C – 24.0°C (default) | Optimize for occupant comfort |
| **Preservation** | No motion (after debounce) | 15.0°C – 28.0°C (default) | Wider range — saves energy but still protects the room from moisture, mold, or material damage from extreme temperatures |

Both ranges are adjustable live from the web dashboard using the +/-
threshold controls; changes apply immediately without re-uploading code.

## Debounce Logic

A `DEBOUNCE_TIME` of 10 seconds prevents the system from rapidly toggling
between occupied/unoccupied states if the PIR sensor briefly stops
detecting motion (e.g., someone sitting still). The system only switches
to "unoccupied" if no motion has been detected for the full debounce
period.
