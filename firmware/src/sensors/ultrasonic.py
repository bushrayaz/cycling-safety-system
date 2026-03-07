"""
ultrasonic.py
---------------------
HC-SR04 Ultrasonic Sensor module for the Cycling Safety System.

Handles:
- Triggering and reading u pto 3 HC-SR04 ultrasonic sensors.
- Spike rejection (ignores readings that jump from previous valid reading)
- Median filtering over a rolling window of the last N valid readings to smooth out noise.
- EMA filtering to give more weight to recent readings while still smoothing out noise.
- Per-sensor confidence scores based on the consistency of recent readings

Directions returned:
- 1 =Front
- 2 =Left
- 3 = Right
- 4 = Rear (optional atm, if rear sensor is implemented)

Usage notes:
- from sensors.ultrasonic import UltrasonicManager
- usm = UltrasonicManager()
- distance, direction, confidence = usm.read_all()
"""

import time
import statistics
import RPi.GPIO as GPIO

# --------------------------
# GPIO PIN CONFIGURATION
# --------------------------

SENSOR_PINS = {
    "left": {"trigger_pin": 23, "echo_pin": 24}, # left sensor
    "right": {"trigger_pin": 17, "echo_pin": 27}, # right sensor
    "front": {"trigger_pin": 5, "echo_pin": 6},   # front sensor
    # 4: {"trigger_pin": 19, "echo_pin": 26}, # Rear sensor (optional)
}

# --------------------------
# SYSTEM PARAMETERS
# --------------------------
SAFE_DISTANCE_CM      = 200.0   # > this -> safe
WARNING_DISTANCE_CM   = 150.0   # object detected, but not an immediate threat
HAZARD_DISTANCE_CM    = 100.0   # unsafe - trigger camera verification
DANGER_DISTANCE_CM    = 50.0    # immediate danger 

MAX_SPIKE_CHANGE_CM   = 80.0    # spike rejection threshold
WINDOW_SIZE           = 5       # median filter window size
EMA_ALPHA             = 0.3     # EMA smoothing factor (0 < alpha < 1)

MIN_VALID_RANGE_CM    = 2.0     # HC_SR04 min reliable range 
MAX_VALID_RANGE_CM    = 400.0   # HC_SR04 max reliable range

VALIDATION_COUNT      = 3       # consecutive hazard reads needed to confirm
TRIGGER_PULSE_S       = 0.00001 # 10µs trigger pulse


# --------------------------
class SensorChannel:
    def __init__(self, name: str, trig_pin: int, echo_pin: int):
        self.name      = name
        self.trig_pin  = trig_pin
        self.echo_pin  = echo_pin

        # rolling buffer of raw valid readings
        self._history: list[float] = []

        # EMA state
        self._ema: float | None = None

        # previous valid reading (for jump detection)
        self._prev_distance: float | None = None

        # consecutive hazard count (for validation)
        self.hazard_counter: int = 0

        # stats for confidence
        self._valid_count   = 0
        self._total_count   = 0

        self._setup_gpio()
#   GPIO ------------------------------------------------
        GPIO.setup(self.trig_pin, GPIO.OUT)
        GPIO.setup(self.echo_pin, GPIO.IN)
        GPIO.output(self.trig_pin, GPIO.LOW)
        time.sleep(0.05)  # let sensor settle

    # Raw distance measurement -------------------------
    def _measure_raw_cm(self) -> float | None:
        """
        Fire a 10 µs trigger pulse, measure the echo duration,
        return distance in cm, or None if the measurement timed out.
        """
        # Send trigger pulse
        GPIO.output(self.trig_pin, GPIO.HIGH)
        time.sleep(TRIGGER_PULSE_S)
        GPIO.output(self.trig_pin, GPIO.LOW)

        timeout = time.time() + 0.04  # 40 ms hard timeout

        # Wait for echo to go HIGH
        pulse_start = time.time()
        while GPIO.input(self.echo_pin) == GPIO.LOW:
            pulse_start = time.time()
            if pulse_start > timeout:
                return None  # no echo received

        # Wait for echo to go LOW
        pulse_end = time.time()
        while GPIO.input(self.echo_pin) == GPIO.HIGH:
            pulse_end = time.time()
            if pulse_end > timeout:
                return None  # echo too long (object too close / stuck)

        duration = pulse_end - pulse_start
        distance = (duration * 34300) / 2  # speed of sound = 343 m/s

        return distance

    # Validity check --------------------------------------
    def _is_valid(d: float | None) -> bool:
        if d is None:
            return False
        return MIN_VALID_RANGE_CM <= d <= MAX_VALID_RANGE_CM

    # Spike rejection --------------------------------------
    def _is_spike(self, d: float) -> bool:
        if self._prev_distance is None:
            return False
        return abs(d - self._prev_distance) > MAX_SPIKE_CHANGE_CM

    # Median filter --------------------------------------
    def _update_history(self, d: float):
        self._history.append(d)
        if len(self._history) > WINDOW_SIZE:
            self._history.pop(0)

    def _median_distance(self) -> float | None:
        if not self._history:
            return None
        return statistics.median(self._history)

    # EMA smoothing --------------------------------------
    def _update_ema(self, median: float) -> float:
        if self._ema is None:
            self._ema = median
        else:
            self._ema = EMA_ALPHA * median + (1 - EMA_ALPHA) * self._ema
        return self._ema

    # Confidence score (0.0 – 1.0) --------------------------------------
    def _compute_confidence(self) -> float:
        self._total_count += 1

        # valid rate component
        valid_rate = self._valid_count / max(self._total_count, 1)

        # stability component: low standard deviation → high confidence
        if len(self._history) >= 2:
            std = statistics.stdev(self._history)
            # normalise: 0 cm std → 1.0, 50 cm std → 0.0
            stability = max(0.0, 1.0 - (std / 50.0))
        else:
            stability = 0.5  # not enough data yet

        # combine equally weighted
        confidence = (valid_rate + stability) / 2.0
        return round(confidence, 3)

    # --------------------------------------
    def read(self) -> tuple[float | None, float]:
        """
        Take one measurement, run full pipeline.

        Returns:
            (filtered_distance_cm, confidence)
            filtered_distance is None when measurement fails completely.
        """
        raw = self._measure_raw_cm()
        self._total_count += 1

        if not self._is_valid(raw):
            # invalid reading — drop it, don't update history
            confidence = self._compute_confidence()
            return None, confidence

        # spike rejection
        if self._is_spike(raw):
            # treat as invalid for this cycle
            confidence = self._compute_confidence()
            return self._ema, confidence  # return last known good EMA

        # reading accepted
        self._valid_count += 1
        self._prev_distance = raw
        self._update_history(raw)

        median  = self._median_distance()
        smoothed = self._update_ema(median)
        confidence = self._compute_confidence()

        return round(smoothed, 2), confidence

    def update_hazard_counter(self, distance: float | None) -> bool:
        """
        Increments or resets the consecutive hazard counter.
        Returns True only once the counter reaches VALIDATION_COUNT.
        """
        if distance is not None and distance < HAZARD_DISTANCE_CM:
            self.hazard_counter += 1
        else:
            self.hazard_counter = 0

        return self.hazard_counter >= VALIDATION_COUNT


# ----------------------------------------------------------
class UltrasonicManager:
    """
    Manages all three ultrasonic sensors.

    Call read_all() every loop iteration.
    It returns the closest confirmed hazard direction and distance.
    """

    DIRECTION_MAP = {
        "front": 1,
        "left":  2,
        "right": 3,
    }

    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        self.channels: dict[str, SensorChannel] = {}
        for name, pins in SENSOR_PINS.items():
            self.channels[name] = SensorChannel(name, pins["trig"], pins["echo"])
        print("[UltrasonicManager] Initialised sensors:", list(self.channels.keys()))

    def read_all(self) -> tuple[float | None, int, float]:
        """
        Read all sensors, return the closest confirmed hazard.

        Returns:
            (hazard_distance_cm, hazard_direction, best_confidence)
            hazard_direction = 0 means no hazard confirmed.
        """
        closest_distance  = None
        closest_direction = 0
        best_confidence   = 0.0

        for name, channel in self.channels.items():
            distance, confidence = channel.read()
            confirmed = channel.update_hazard_counter(distance)

            if confirmed and distance is not None:
                if closest_distance is None or distance < closest_distance:
                    closest_distance  = distance
                    closest_direction = self.DIRECTION_MAP.get(name, 0)
                    best_confidence   = confidence

        return closest_distance, closest_direction, best_confidence

    def cleanup(self):
        """Call this on shutdown to release GPIO resources."""
        GPIO.cleanup()
        print("[UltrasonicManager] GPIO cleaned up.")


