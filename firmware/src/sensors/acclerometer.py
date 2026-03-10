"""
accelerometer.py
---------------------
Accelerometer module for the Cycling Safety System.

Handles:
- Initialising MPU6050 accelerometer via I2C
- Reading acceleration values (ax, ay, az)
- Maintaining an acceleration history buffer
- Providing data for crash detection algorithms

Usage:
- from sensors.accelerometer import AccelerometerManager
- accel = AccelerometerManager()
- ax, ay, az = accel.read()
"""

import time
from collections import deque

try:
    import smbus2
    I2C_AVAILABLE = True
except ImportError:
    I2C_AVAILABLE = False


# Sensor Configuration

I2C_BUS = 1
MPU_ADDR = 0x68

PWR_MGMT_1 = 0x6B
ACCEL_XOUT = 0x3B

ACCEL_SCALE = 16384.0

BUFFER_SIZE = 50


# --------------------------
class AccelerometerManager:

    def __init__(self):

        self.bus = None
        self.initialised = False

        self.accelerationBuffer = deque(maxlen=BUFFER_SIZE)

        self._init_sensor()

    def _init_sensor(self):

        if not I2C_AVAILABLE:
            return

        try:
            self.bus = smbus2.SMBus(I2C_BUS)

            # wake sensor
            self.bus.write_byte_data(MPU_ADDR, PWR_MGMT_1, 0)

            self.initialised = True
            print("Accelerometer Initialised")

        except Exception as e:
            print(f"Accelerometer Init failed: {e}")

    def _read_word(self, reg):

        high = self.bus.read_byte_data(MPU_ADDR, reg)
        low = self.bus.read_byte_data(MPU_ADDR, reg + 1)

        value = (high << 8) + low

        if value >= 0x8000:
            value = -((65535 - value) + 1)

        return value

    def read(self):

        if not self.initialised:
            return 0.0, 0.0, 0.0

        try:

            raw_ax = self._read_word(ACCEL_XOUT)
            raw_ay = self._read_word(ACCEL_XOUT + 2)
            raw_az = self._read_word(ACCEL_XOUT + 4)

            ax = raw_ax / ACCEL_SCALE
            ay = raw_ay / ACCEL_SCALE
            az = raw_az / ACCEL_SCALE

            self.accelerationBuffer.append((ax, ay, az))

            return round(ax,3), round(ay,3), round(az,3)

        except Exception as e:
            print(f"Accelerometer Read failed: {e}")
            return 0.0, 0.0, 0.0