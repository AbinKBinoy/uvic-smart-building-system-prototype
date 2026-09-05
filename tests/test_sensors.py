# ============================================================================
# Smart BMS - Sensor & LED Test Code (No Wi-Fi)
# ENGR 120 - University of Victoria
# ============================================================================
# Use this to test all sensors and LEDs before adding Wi-Fi.
# Watch the serial monitor in Thonny to see live readings.
# ============================================================================

from machine import Pin, ADC
import time
import math

# --- Output LEDs ---
led_lights  = Pin(18, Pin.OUT)  # white LED (lighting)
led_heating = Pin(16, Pin.OUT)  # red LED (heating)
led_cooling = Pin(17, Pin.OUT)  # green LED (cooling)
pico_led    = Pin("LED", Pin.OUT)

# --- Input Sensors ---
motion_sensor = Pin(28, Pin.IN, Pin.PULL_DOWN)  # PIR
temp_sensor   = ADC(26)  # thermistor on ADC0
light_sensor  = ADC(27)  # LDR on ADC1

# --- Thermistor Constants ---
R0 = 10000    # 10kΩ at 25°C
T0 = 298.15   # 25°C in Kelvin
B  = 3960     # beta constant

# --- Thresholds ---
LIGHT_THRESHOLD = 40000  # adjust after testing

# Temperature thresholds (°C)
COMFORT_LOW  = 20.0   # occupied: heating below this
COMFORT_HIGH = 24.0   # occupied: cooling above this
PRESERVE_LOW  = 15.0  # unoccupied: heating below this
PRESERVE_HIGH = 28.0  # unoccupied: cooling above this

DEBOUNCE_TIME = 10  # seconds


# --- Sensor Functions ---
def read_temperature():
    try:
        adc = temp_sensor.read_u16()
        if adc <= 0 or adc >= 65535:
            return None
        # Same as prof's formula: round(((1/(1/298+(1/3960)*math.log((65535/adc-1))))-273)*1),1)
        resistance = R0 * (65535.0 / adc - 1.0)
        temp_k = 1.0 / ((1.0 / T0) + (1.0 / B) * math.log(resistance / R0))
        temp_c = temp_k - 273.15
        return round(temp_c, 1)
    except:
        return None


def read_light():
    adc = light_sensor.read_u16()
    if adc >= LIGHT_THRESHOLD:
        return adc, "Dark"
    else:
        return adc, "Bright"


# --- Main Program ---
print("=" * 40)
print("BMS Sensor Test - No Wi-Fi")
print("=" * 40)

# Turn everything off
led_lights.off()
led_heating.off()
led_cooling.off()
pico_led.on()

# PIR calibration
print("PIR calibrating... wait 15 seconds")
time.sleep(15)
print("PIR ready!")
print("=" * 40)

# State variables
motion_state = False
last_motion_time = 0

while True:
    current_time = time.time()
    
    # --- Read sensors ---
    motion_val = motion_sensor.value()
    temp = read_temperature()
    light_adc, light_status = read_light()
    
    # --- Occupancy logic ---
    if motion_val == 1:
        if not motion_state:
            print(">>> MOTION DETECTED - OCCUPIED")
        motion_state = True
        last_motion_time = current_time
    elif motion_val == 0:
        if motion_state and (current_time - last_motion_time >= DEBOUNCE_TIME):
            print(">>> NO MOTION - UNOCCUPIED")
            motion_state = False
    
    # --- Lighting control ---
    if motion_state and light_status == "Dark":
        led_lights.on()
        light_action = "On"
    else:
        led_lights.off()
        light_action = "Off"
    
    # --- HVAC control ---
    hvac_action = "Off"
    if temp is not None:
        if motion_state:
            low, high = COMFORT_LOW, COMFORT_HIGH
        else:
            low, high = PRESERVE_LOW, PRESERVE_HIGH
        
        if temp < low:
            led_heating.on()
            led_cooling.off()
            hvac_action = "Heating (red)"
        elif temp > high:
            led_cooling.on()
            led_heating.off()
            hvac_action = "Cooling (green)"
        else:
            led_heating.off()
            led_cooling.off()
    
    # --- Print everything ---
    mode = "OCCUPIED" if motion_state else "UNOCCUPIED"
    print(f"[{mode}] Temp: {temp}°C | Light: {light_status} ({light_adc}) | Lights: {light_action} | HVAC: {hvac_action}")
    
    time.sleep(2)
