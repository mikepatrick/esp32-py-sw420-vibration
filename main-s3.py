import time

import machine

# Define pins
S3_VIBRATION_PIN = 13
C3_VIBRATION_PIN = 4
vibration_pin = machine.Pin(S3_VIBRATION_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
led_pin = machine.Pin(2, machine.Pin.OUT)

# Flag to track state change
vibration_detected = False

# Interrupt handler function
def handle_vibration(pin):
    global vibration_detected
    vibration_detected = True

# Configure hardware interrupt to trigger on any state transition
vibration_pin.irq(trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING, handler=handle_vibration)

print("SW-420 Sensor Monitoring Started.")

while True:
    if vibration_detected:
        print("⚠️ Motion detected!")
        led_pin.value(1)   # Turn LED on

        time.sleep_ms(500) # Hold for visibility

        led_pin.value(0)   # Turn LED off
        vibration_detected = False # Reset the flag

    time.sleep_ms(10) # Tiny power-saving pause in the polling loop
