"""
led.py
---------------------
LED module for the Cycling Safety System.

Handles:
- Left and right turn signals
- Basic blinking control
- System visual alerts

Usage:
- from actuators.led import LEDController
- leds = LEDController()
- leds.set_left(True)
"""

import time
import RPi.GPIO as GPIO


# --------------------------
# GPIO CONFIG
# --------------------------

LEFT_LED_PIN = 16
RIGHT_LED_PIN = 20

BLINK_INTERVAL = 0.5


# --------------------------
class LEDController:

    def __init__(self):

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        GPIO.setup(LEFT_LED_PIN, GPIO.OUT)
        GPIO.setup(RIGHT_LED_PIN, GPIO.OUT)

        self.blink_state = False
        self.last_toggle = time.time()

        print("LED Controller initialised")

    def _blink(self):

        now = time.time()

        if now - self.last_toggle > BLINK_INTERVAL:
            self.blink_state = not self.blink_state
            self.last_toggle = now

        return self.blink_state

    def set_left(self, enabled: bool):

        if enabled:
            GPIO.output(LEFT_LED_PIN, self._blink())
        else:
            GPIO.output(LEFT_LED_PIN, GPIO.LOW)

    def set_right(self, enabled: bool):

        if enabled:
            GPIO.output(RIGHT_LED_PIN, self._blink())
        else:
            GPIO.output(RIGHT_LED_PIN, GPIO.LOW)

    def off(self):

        GPIO.output(LEFT_LED_PIN, GPIO.LOW)
        GPIO.output(RIGHT_LED_PIN, GPIO.LOW)

    def cleanup(self):

        GPIO.cleanup()
        print("LED GPIO cleaned up")