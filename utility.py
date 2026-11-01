import time

import network
import ntptime

import ssd1306

# from lib.rotary_irq_esp import RotaryIRQ

def load_env(filepath: str = ".env") -> dict[str, str]:
    env_vars: dict[str, str] = {}
    try:
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines or comments
                if not line or line.startswith("#"):
                    continue
                # Split at the first '='
                if "=" in line:
                    key, value = line.split("=", 1)
                    # Strip spaces and optional surrounding quotes
                    key = key.strip()
                    value = value.strip().strip("'").strip('"')
                    env_vars[key] = value
    except OSError:
        print(f"Warning: {filepath} file not found.")
    return env_vars

ENVVARS = load_env()
trace_enabled = ENVVARS.get("TRACE_ENABLED")
TRACE_ENABLED = trace_enabled and trace_enabled.upper() != "FALSE" and trace_enabled != "0"

def show_oled_rotated_90(oled: ssd1306.SSD1306_I2C, rot_buf: ssd1306.SSD1306_I2C):
	oled.fill(0)
	for y in range(128):
		for x in range(64):
			oled.pixel(127 - y, x, rot_buf.pixel(x, y))
	oled.show()

def show_oled_rotated_270(oled: ssd1306.SSD1306_I2C, rot_buf: ssd1306.SSD1306_I2C):
	oled.fill(0)
	for y in range(128):
		for x in range(64):
			oled.pixel(y, 63 - x, rot_buf.pixel(x, y))
	oled.show()

def paint_oled_270(oled: ssd1306.SSD1306_I2C, rot_buf: ssd1306.SSD1306_I2C, text: str, x: int = 10, y: int = 10):
	"""Paint text on the rotated OLED display."""
	rot_buf.fill(0)
	rot_buf.text(text, x, y)
	show_oled_rotated_270(oled, rot_buf)

def paint_oled(oled: ssd1306.SSD1306_I2C, text: str, x: int = 10, y: int = 10):
	"""Paint text on an OLED display."""
	oled.fill(0)
	oled.text(text, x, y)
	oled.show()

def paint_oled_list(oled: ssd1306.SSD1306_I2C, text: list[str], x: int = 10, y: int = 10):
	"""Write a list of strings to an OLED display."""
	oled.fill(0)
	for i, line in enumerate(text):
		oled.text(line, x, y + (i * 10))  # Adjust line spacing as needed
	oled.show()

# def configure_rotary_encoder(pin_clk: int, pin_dt: int, min_val: int = 0, max_val: int = 3) -> RotaryIRQ:
#     """Configure a rotary encoder with the specified parameters."""
#     r = RotaryIRQ(pin_num_clk=pin_clk,
#                   pin_num_dt=pin_dt,
#                   min_val=min_val,
#                   max_val=max_val,
#                   reverse=False,
#                   pull_up=True,
#                   range_mode=RotaryIRQ.RANGE_WRAP)
#     return r

def connect_wifi(env_vars: dict[str, str] = ENVVARS) -> bool:
    """Connects the ESP32 to the local Wi-Fi network."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    # 3. LOWER TRANSMIT POWER (Crucial for ESP32-C3 Super Mini)
    # Default is often 78 (19.5 dBm). Dropping it to 40 (approx. 10 dBm) or 34 (approx. 8.5 dBm)
    # keeps current consumption below the brownout threshold of the tiny regulator.
    try:
        # Syntax: wlan.config(txpower=value)
        # Value is in quarter-dBm units (e.g., 34 = 8.5 dBm, 40 = 10 dBm)
        wlan.config(txpower=8.5)
        print("TX Power reduced to 8.5 dBm.")
    except Exception as e:
        print("Could not set TX power:", e)
    if not wlan.isconnected():
        print(f"Connecting to {env_vars.get('WIFI_NETWORK')}...")
        wlan.connect(env_vars.get('WIFI_NETWORK'), env_vars.get('WIFI_PASSWORD'))

        # Wait for connection (timeout after 15 seconds)
        timeout = 30
        start_time = time.time()
        while not wlan.isconnected():
            if time.time() - start_time > timeout:
                print("Wi-Fi connection timed out!")
                return False
            trace("WIFI Connecting....")
            time.sleep(0.5)

    print("Connected! IP Info:", wlan.ifconfig())
    return True

def sync_ntp_time():
    """Fetches the current UTC time from an NTP server and sets the internal RTC."""
    try:
        print("Syncing time with NTP server...")
        # ntptime.settime() fetches UTC time from pool.ntp.org and sets the hardware RTC
        ntptime.settime()
        print("Time synchronized successfully!")
    except Exception as e:
        print("Failed to sync NTP time:", e)

def get_time_and_date_strings(utc_offset_hours: int = -5) -> tuple[str, str]:
	"""Returns the current time and date as formatted strings, adjusted for the specified UTC offset."""
	current_time = time.time()
	local_time = current_time + (utc_offset_hours * 3600)  # Adjust for your timezone
	local_tuple = time.localtime(local_time)
	year, month, day, hour, minute, second, _, _ = local_tuple[0:8]
	time_str = f"{hour:02d}:{minute:02d}"
	date_str = f"{year}-{month:02d}-{day:02d}"
	return time_str, date_str

def log(msg: str) -> None:
    print(msg)

def trace(msg: str) -> None:
    if TRACE_ENABLED:
        log(msg)
