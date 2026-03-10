"""
camera.py
---------------------
Raspberry Pi AI Camera (IMX500) module for the Cycling Safety System.

Handles:
- Initialising the PiCamera interface with the IMX500 AI Camera.
- Running YOLO inference on captured frames to detect objects relevant
  to cycling safety (e.g., vehicles, pedestrians).
- Computing a camera confidence score 
- Only activating when the ultrasonic gate gives the go-ahead signal to save power.

Hazard classes to detect:
- Vehicles (cars, trucks, buses)
- Pedestrians
- Cyclists

"""
import time
from collections import deque

try:
    from picamera2 import Picamera2
    PICAMERA_AVAILABLE = True
except ImportError:
    PICAMERA_AVAILABLE = False
    print("WARNING: Picamera2 library not found - running in mock mode ")

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("WARNING: Ultralytics YOLO library not found - running in mock mode ")


# --------------------------
# CONFIGURATION
# --------------------------

# Path to the YOLO model weights (custom trained for cycling safety)
# After training on roboflow, export the model as:
#    model.export(format="ncnn") - best for Pi 5
# Then point YOLO_MODEL_PATH at the exported folder / .pt file
YOLO_MODEL_PATH = "models/cycling_hazard_yolov8n_ncnn_model"

# Classes the model was trained to detect (must match the training dataset)
HAZARD_CLASSES = ["car", "truck", "bus", "pedestrian", "bicycle"]

# Minimum confidence threshold for detections to be considered valid
CONFIDENCE_THRESHOLD = 0.5

# Camera must see a hazard class in at least this many of the last N frames to trigger an alert
DETECTION_HISTORY_SIZE = 10  # Keep track of the last 10 frames
MIN_FRAMES_WITH_HAZARD = 3   # If at least 3 of the last 10 frames contain a valid hazard detection, we consider it a real threat

# Camera resolution and framerate settings
CAMERA_RESOLUTION = (640, 480)
CAMERA_FRAMERATE = 15

# Region of Interest
# Values are fractions of the frame dimensions
ROI = (0.1, 0.0, 0.9, 0.8)  # (x_min, y_min, x_max, y_max) - focus on the area around the cyclist


# ------------------------------------------------------
class CameraHazardDetector:
    def __init__(self):
        self._camera = None
        self._model = None
        self._running = False  # FIX: initialise here so it always exists

        self.detection_history: deque[bool] = deque(maxlen=DETECTION_HISTORY_SIZE)

        self._init_camera()
        self._init_model()

    def _init_camera(self):
        if not PICAMERA_AVAILABLE:
            print("[Camera] Mock camera mode enabled - no hardware detected.")
            return
        try:
            self._camera = Picamera2()
            config = self._camera.create_preview_configuration(
                main={"format": "RGB888", "size": CAMERA_RESOLUTION}
            )
            self._camera.configure(config)
            self._camera.start()
            self._running = True
            time.sleep(1)
            print("[Camera] Camera initialized successfully.")  # FIX: printf → print
        except Exception as e:
            print(f"[Camera] Failed to initialize camera: {e}")

    def _init_model(self):
        if not YOLO_AVAILABLE:
            print("[Camera] Mock model mode enabled - no YOLO library detected.")
            return
        try:
            self._model = YOLO(YOLO_MODEL_PATH)
            print("[Camera] YOLO model loaded successfully.")  # FIX: printf → print
        except Exception as e:
            print(f"[Camera] Failed to load YOLO model: {e}")

    # Frame capture
    def capture_frame(self):
        if not self._running or self._camera is None:
            print("[Camera] No camera available - cannot capture frame.")
            return None
        try:
            frame = self._camera.capture_array()
            return frame
        except Exception as e:
            print(f"[Camera] Failed to capture frame: {e}")
            return None

    # ROI cropping helper
    @staticmethod
    def _apply_roi(frame):
        if frame is None:
            return None
        h, w = frame.shape[:2]  # FIX: shape[:2] returns 2 values, not 3
        x_min = int(ROI[0] * w)
        y_min = int(ROI[1] * h)
        x_max = int(ROI[2] * w)
        y_max = int(ROI[3] * h)
        return frame[y_min:y_max, x_min:x_max]

    # YOLO inference
    def detect_hazards(self, frame):
        """
        Run YOLO inference on the given frame.
        Returns:
            (hazard_found: bool, confidence: float)
        """
        if self._model is None or frame is None:
            print("[Camera] No model available - cannot perform detection.")
            return False, 0.0

        results = self._model(frame, verbose=False)

        best_conf = 0.0
        hazard_found = False

        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                label = result.names[cls_id].lower()
                conf = float(box.conf[0])
                if label in HAZARD_CLASSES and conf >= CONFIDENCE_THRESHOLD:  # FIX: use CONFIDENCE_THRESHOLD
                    hazard_found = True
                    if conf > best_conf:
                        best_conf = conf

        return hazard_found, round(best_conf, 3)

    # Frame consistency check
    def check_history(self):
        if len(self.detection_history) < DETECTION_HISTORY_SIZE:
            return False
        count_hazards = sum(self.detection_history)
        return count_hazards >= MIN_FRAMES_WITH_HAZARD

    def check(self):
        """
        Main method to be called by the system.
        Captures one frame, runs detection, updates history,
        and returns (confirmed_hazard, confidence).
        """
        frame = self.capture_frame()
        roi_frame = self._apply_roi(frame)
        found, conf = self.detect_hazards(roi_frame)  # FIX: was self._run (incomplete)

        self.detection_history.append(found)
        confirmed_hazard = self.check_history()

        return confirmed_hazard, conf

    def shutdown(self):
        if self._camera is not None and self._running:
            self._camera.stop()
            self._running = False
            print("[Camera] Camera shutdown successfully.")