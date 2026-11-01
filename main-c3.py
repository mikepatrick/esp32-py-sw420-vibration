import time

import micropython
from machine import I2C, Pin

import ssd1306
from utility import (connect_wifi, get_time_and_date_strings, paint_oled,
                     sync_ntp_time, trace)

# Emergency exception buffer allocation for stable Ctrl+C operation
micropython.alloc_emergency_exception_buf(100)

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
MAX_HISTORY = 3            # Keeps 3 items on screen without vertical clipping
run_history: list[dict[str, object]] = []           # Array of dictionaries: {'time': 'HH:MM', 'duration': X}

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

def update_oled_history_display(status_text):
    """Clears the display and repaints a structured view with rolling history logs."""
    oled.fill(0)

    # Line 0 & 1: Display the current operational state and live clock
    time_str, date_str = get_time_and_date_strings()
    oled.text(f"STATUS: {status_text}", 0, 0)
    oled.text(f"TIME  : {time_str}", 0, 10)
    oled.text("----------------", 0, 20)

    # Lines 3, 4, 5: Render the historical entries (newest on top)
    start_y = 32
    row_spacing = 10
    for i, record in enumerate(reversed(run_history)):
        row_y = start_y + (i * row_spacing)
        oled.text(f"{record['time']} -> {record['duration']}s", 0, row_y)

    oled.show()

def add_to_history(time_stamp, duration_seconds):
    """Maintains a sliding history list bounded by MAX_HISTORY size constraints."""
    global run_history
    run_history.append({'time': time_stamp, 'duration': duration_seconds})
    if len(run_history) > MAX_HISTORY:
        run_history.pop(0)

def monitor_pump():
    print("Calibrating... Keep sensor still.")
    time.sleep(1)
    print("Pump monitoring active.")
    update_oled_history_display("MONITOR")

    last_state = sensor_pin.value()
    last_vibration_time = 0
    first_vibration_time = 0
    pump_start_time = 0
    start_time_str = ""

    is_shaking = False      # Tracks if the spring is physically moving right now
    pump_is_running = False  # Tracks your official validated pump status

    while True:
        # Keep REPL loop and mpremote fully responsive to terminal inputs
        time.sleep_ms(0)

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
                pump_start_time = current_time
                start_time_str, _ = get_time_and_date_strings()

                print("[PUMP STATUS] RUNNING - Sustained vibration validated!")
                update_oled_history_display("RUNNING")

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

                    # Deduct the debounce tail timeout window for exact net measurement
                    total_run_ms = time.ticks_diff(current_time, pump_start_time) - DEBOUNCE_WINDOW_MS
                    duration_seconds = round(max(0, total_run_ms) / 1000.0, 1)

                    print(f"[PUMP STATUS] STOPPED - Net Duration: {duration_seconds}s")
                    print("[PUMP STATUS] STOPPED - Pump is idle.")

                    # Add data context metrics into our array
                    add_to_history(start_time_str, duration_seconds)
                    update_oled_history_display("IDLE")
                else:
                    print("[FILTERED] Ignored a brief vibration spike.")
                    update_oled_history_display("IDLE")
        trace(f"End of loop - sleeping {POLL_DELAY_MS} ms.")
        time.sleep_ms(POLL_DELAY_MS)

connect_wifi()
sync_ntp_time()

try:
    monitor_pump()
except KeyboardInterrupt:
    print("\nStopped.")
