import time

from machine import I2C, Pin

import ssd1306
from utility import (connect_wifi, get_time_and_date_strings, paint_oled,
                     sync_ntp_time, trace)

# Define pins
S3_VIBRATION_PIN = 13
C3_VIBRATION_PIN = 4
OLED_SDA_PIN = 5
OLED_SCL_PIN = 6

# --- Configuration Parameters ---
DEBOUNCE_WINDOW_MS = 3500  # How long it must be dead still before declaring it stopped
REQUIRED_RUN_MS = 5500      # MUST shake continuously for this long to count as running
POLL_DELAY_MS = 20         # Sample rate

oled_width = 128
oled_height = 64

print("Loading environment variables")
print(f"Setting vibration data pin to {C3_VIBRATION_PIN}")
sensor_pin = Pin(C3_VIBRATION_PIN, mode=Pin.IN)
# led_pin = machine.Pin(2, machine.Pin.OUT)

print(f"Configuring OLED display: SCL {OLED_SCL_PIN}, SDA {OLED_SDA_PIN}")
try:
    i2c_1 = I2C(0,
                scl=Pin(OLED_SCL_PIN, Pin.PULL_UP),
                sda=Pin(OLED_SDA_PIN, Pin.PULL_UP), freq=400000)
    time.sleep_ms(100)
except:
    print("Error creating I2C object.  Check pin assignments and wiring.")
    raise

try:
    oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c_1)
    time.sleep_ms(100)
except:
    print("Error creating OLED objects.  Check I2C setup and wiring.")
    raise

print("Painting OLED display")
paint_oled(oled, "Initializing...")

def monitor_pump():
    print("Calibrating... Keep sensor still.")
    time.sleep(1)
    print("Pump monitoring active.")
    paint_oled(oled, "Monitoring...")

    last_state = sensor_pin.value()
    last_vibration_time = 0
    first_vibration_time = 0

    is_shaking = False      # Tracks if the spring is physically moving right now
    pump_is_running = False  # Tracks your official validated pump status

    while True:
        current_state = sensor_pin.value()
        current_time = time.ticks_ms()

        # 1. DETECT PHYSICAL MOTION
        if current_state != last_state:
            trace(f"State changed from {last_state} to {current_state}")
            last_vibration_time = current_time
            last_state = current_state

            if not is_shaking:
                trace("is_shaking set to true")
                is_shaking = True
                # Mark exactly when this burst of shaking started
                first_vibration_time = current_time
                trace(f"first_vibration_time: {first_vibration_time}")

        # 2. VALIDATE SUSTAINED SHAKING (SENSITIVITY FILTER)
        if is_shaking and not pump_is_running:
            trace("is_shaking and pump_is_running both TRUE")
            # How long has it been continuously shaking?
            shake_duration = time.ticks_diff(current_time, first_vibration_time)
            trace(f"shake duration: {shake_duration}")
            if shake_duration >= REQUIRED_RUN_MS:
                trace(f"Shake threshold ({REQUIRED_RUN_MS}) reached.  pump_is_running_set to TRUE")
                pump_is_running = True
                print("[PUMP STATUS] RUNNING - Sustained vibration validated!")
                time_str, _ = get_time_and_date_strings()
                paint_oled(oled, f"PUMP RUNNING {time_str}")

        # 3. DETECT MOTION STOPPED
        if is_shaking:
            trace("Detect motion stopped")
            time_since_last_hit = time.ticks_diff(current_time, last_vibration_time)
            trace(f"Time since last hit: {time_since_last_hit}")
            if time_since_last_hit > DEBOUNCE_WINDOW_MS:
                trace(f"Stop threshold ({DEBOUNCE_WINDOW_MS}) reached.  is_shaking set to FALSE")
                is_shaking = False

                # Only print stopped if it was actually validated as running
                if pump_is_running:
                    pump_is_running = False
                    print("[PUMP STATUS] STOPPED - Pump is idle.")
                    time_str, _ = get_time_and_date_strings()
                    paint_oled(oled, f"PUMP STOPPED")
                else:
                    print("[FILTERED] Ignored a brief vibration spike.")
        trace(f"End of loop - sleeping {POLL_DELAY_MS} ms.")
        time.sleep_ms(POLL_DELAY_MS)

connect_wifi()
sync_ntp_time()

try:
    monitor_pump()
except KeyboardInterrupt:
    print("\nStopped.")