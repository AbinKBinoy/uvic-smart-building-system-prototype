# Circuit Notes

## Block Diagram

```
 INPUTS                    RASPBERRY PI PICO W                OUTPUTS
┌────────────┐                                              ┌──────────────┐
│ PIR Sensor │──── digital ────▶┌──────────────┐             │ White LED     │
└────────────┘                  │              │──GPIO18───▶│ (Lighting)    │
┌────────────┐                  │  Control     │             └──────────────┘
│Photoresistor│──── ADC1 ───────▶│  Logic +     │             ┌──────────────┐
│ (LDR)      │                  │  Wi-Fi       │──GPIO16───▶│ Red LED       │
└────────────┘                  │  Server      │             │ (Heating)     │
┌────────────┐                  │              │             └──────────────┘
│ Thermistor  │──── ADC0 ───────▶│              │──GPIO17───▶┌──────────────┐
│ (NTC 10kΩ) │                  └──────────────┘             │ Green LED     │
└────────────┘                                                │ (Cooling)     │
                                                                └──────────────┘
```

## Pin Assignments

| Signal              | Pico W Pin | GPIO | Type          |
|----------------------|------------|------|----------------|
| PIR motion sensor     | Physical 34 | GP28 | Digital input (pull-down) |
| Photoresistor (LDR)   | Physical 32 | GP27 (ADC1) | Analog input |
| NTC Thermistor        | Physical 31 | GP26 (ADC0) | Analog input |
| White LED (lighting)  | Physical 24 | GP18 | Digital output |
| Red LED (heating)     | Physical 21 | GP16 | Digital output |
| Green LED (cooling)   | Physical 22 | GP17 | Digital output |

## Voltage Divider Circuits

Both the thermistor and the LDR use a simple voltage divider:

```
        3.3V
         │
       ┌───┐
       │ R │  ← Sensor (thermistor or LDR)
       └───┘
         │
         ├──────▶ To ADC pin
         │
       ┌───┐
       │ R │  ← Fixed 10 kΩ resistor
       └───┘
         │
        GND
```

**Correct orientation:** the sensor goes on top (connected to 3.3V), the
fixed 10 kΩ resistor goes on the bottom (connected to GND). The ADC reads
the voltage at the midpoint.

### ⚠️ Common mistake: reversed orientation

If the sensor and fixed resistor are swapped (fixed resistor on top,
sensor on bottom), the ADC readings will be **inverted**:

- **Thermistor reversed:** temperature reading goes *down* when the
  thermistor is heated (should go up)
- **LDR reversed:** covering the LDR reads as "Bright" and shining a light
  on it reads as "Dark" (should be the opposite)

**Two ways to fix this:**
1. **Hardware fix (recommended):** physically swap the sensor and fixed
   resistor positions on the breadboard to match the diagram above
2. **Software fix:** flip the comparison operator in the corresponding
   `read_*()` function in `main.py` (used temporarily during development
   before the hardware was corrected)

Both fixes were used at different points during this project's development
— see the reversed comparisons in `read_light()` if you need to adjust for
your specific wiring.

## LED Driving Circuit

Each LED has a current-limiting resistor between the GPIO pin and the LED
anode, per LED datasheet safety guidance (100–330 Ω range):

```
GPIO pin ──[100Ω resistor]──▶|── GND
                            LED
                       (anode → cathode)
```

100 Ω resistors were used for all three LEDs in this build.

## Temperature Conversion — Steinhart-Hart Beta Equation

The thermistor's resistance is converted to temperature using:

```
1/T = 1/T0 + (1/B) * ln(R / R0)
```

Where:
- `T`  = temperature in Kelvin (solved for)
- `T0` = 298.15 K (25°C reference temperature)
- `B`  = 3960 (Beta constant, from datasheet, ±1%)
- `R0` = 10,000 Ω (thermistor resistance at 25°C, from datasheet)
- `R`  = thermistor's current resistance, calculated from the ADC reading:

```
R = R0 * (65535 / ADC_value - 1)
```

This assumes the fixed resistor in the voltage divider equals `R0`
(10 kΩ). If a different fixed resistor value is used, this calculation
must be adjusted accordingly.

Final conversion to Celsius:
```
T(°C) = T(Kelvin) - 273.15
```

## Calibrating the Light Threshold

The `LIGHT_THRESHOLD` constant in `main.py` (default `40000`) determines
the ADC value that separates "Dark" from "Bright." This depends on:
- The specific LDR used
- The fixed resistor value paired with it
- Ambient lighting conditions in the room

**To calibrate:**
1. Run `tests/test_sensors.py` (no Wi-Fi needed)
2. Watch the raw ADC value printed to the serial monitor
3. Note the value with the LDR fully lit vs. fully covered
4. Set `LIGHT_THRESHOLD` to roughly the midpoint between those two values

## Bill of Materials

| Qty | Component | Notes |
|-----|-----------|-------|
| 1 | Raspberry Pi Pico W | Must be the **W** variant for Wi-Fi |
| 1 | PIR motion sensor module | |
| 1 | Photoresistor (LDR) | |
| 1 | NTC Thermistor (10 kΩ @ 25°C, B=3960) | |
| 2 | 10 kΩ resistor | For voltage dividers |
| 1 | White LED | Lighting indicator |
| 1 | Red LED | Heating indicator |
| 1 | Green LED | Cooling indicator |
| 3 | 100 Ω resistor | LED current limiting |
| 1 | Breadboard | |
| — | Jumper wires | |
