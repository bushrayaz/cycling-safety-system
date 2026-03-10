"""
gyroscope.py
---------------------
Gyroscope module for the Cycling Safety System.

Handles:
- Initialising MPU6050 gyroscope
- Reading angular velocity values (gx, gy, gz)
- Providing motion rotation data for crash detection

Usage:
- from sensors.gyroscope import GyroscopeManager
- gyro = GyroscopeManager()
- gx, gy, gz = gyro.read()
"""

try:
    import smbus2
    I2C_AVAILABLE = True
except ImportError:
    I2C_AVAILABLE = False


# Sensor Config

I2C_BUS = 1
MPU_ADDR = 0x68

PWR_MGMT_1 = 0x6B
GYRO_XOUT = 0x43

GYRO_SCALE = 131.0


# --------------------------
class GyroscopeManager:

    def __init__(self):

        self.bus = None
        self.initialised = False

        self._init_sensor()

    def _init_sensor(self):

        if not I2C_AVAILABLE:
            return

        try:
            self.bus = smbus2.SMBus(I2C_BUS)

            self.bus.write_byte_data(MPU_ADDR, PWR_MGMT_1, 0)

            self.initialised = True
            #print("[Gyroscope] Initialised")

        except Exception as e:
            print(f"Gyroscope Init failed: {e}")

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

            raw_gx = self._read_word(GYRO_XOUT)
            raw_gy = self._read_word(GYRO_XOUT + 2)
            raw_gz = self._read_word(GYRO_XOUT + 4)

            gx = raw_gx / GYRO_SCALE
            gy = raw_gy / GYRO_SCALE
            gz = raw_gz / GYRO_SCALE

            return round(gx,3), round(gy,3), round(gz,3)

        except Exception as e:
            print(f"Gyroscope Read failed: {e}")
            return 0.0, 0.0, 0.0