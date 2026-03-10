"""
test_sensors.py
---------------
Test to verify that the ultrasonic sensor & camera module
are working directly on the Raspberry Pi before integrating with main.py.

Usage:
    cd cycling-safety-system/firmware/src
    python3 tests/test_sensors.py --ultrasonic      # test sensors only
    python3 tests/test_sensors.py --camera          # test camera only
    python3 tests/test_sensors.py --both            # test both together (fusion demo)

Press Ctrl+C to stop.
"""

import sys
import time
import argparse

# Allow running from the src/ directory
sys.path.insert(0, ".")

DIRECTION_LABELS = {0: "NONE", 1: "FRONT", 2: "LEFT", 3: "RIGHT", 4: "REAR"}


# ─────────────────────────────────────────────────────────────────
def test_ultrasonic(loop_count: int = 0):
    """
    Continuously print distance, direction, and confidence from all sensors.
    loop_count=0 means run forever.
    """
    from sensors.ultrasonic import UltrasonicManager, HAZARD_DISTANCE_CM

    print("\n══ ULTRASONIC TEST ══════════════════════════════════")
    print(f"  Hazard threshold : {HAZARD_DISTANCE_CM} cm")
    print("  Press Ctrl+C to stop.\n")

    usm = UltrasonicManager()
    i = 0
    try:
        while loop_count == 0 or i < loop_count:
            distance, direction, confidence = usm.read_all()
            label = DIRECTION_LABELS.get(direction, "?")

            if distance is None:
                status = "CLEAR"
                dist_str = "  ---  "
            else:
                status = "⚠ HAZARD" if direction != 0 else "CLEAR"
                dist_str = f"{distance:6.1f} cm"

            print(
                f"  [{label:5s}]  distance={dist_str}  "
                f"confidence={confidence:.2f}  status={status}"
            )
            time.sleep(0.1)
            i += 1
    except KeyboardInterrupt:
        print("\n[Test] Stopped by user.")
    finally:
        usm.cleanup()


# ─────────────────────────────────────────────────────────────────
def test_camera(loop_count: int = 0):
    """
    Continuously capture frames and report whether a hazard was detected.
    loop_count=0 means run forever.
    """
    from sensors.camera import CameraHazardDetector

    print("\n══ CAMERA TEST ══════════════════════════════════════")
    print("  Watching for: car, truck, bus, pedestrian, bicycle")
    print("  Press Ctrl+C to stop.\n")

    cam = CameraHazardDetector()
    i = 0
    try:
        while loop_count == 0 or i < loop_count:
            confirmed, conf = cam.check()
            status = "🚨 HAZARD CONFIRMED" if confirmed else "clear"
            print(f"  Camera → confirmed={confirmed}  confidence={conf:.3f}  [{status}]")
            time.sleep(0.2)
            i += 1
    except KeyboardInterrupt:
        print("\n[Test] Stopped by user.")
    finally:
        cam.shutdown()  # FIX: was cam.stop() — method is called shutdown()


# ─────────────────────────────────────────────────────────────────
def test_fusion(loop_count: int = 0):
    """
    Demonstrates the ultrasonic-gates-camera fusion logic:
    Camera only activates when ultrasonic detects something within hazard range.
    """
    from sensors.ultrasonic import UltrasonicManager, HAZARD_DISTANCE_CM
    from sensors.camera import CameraHazardDetector

    print("\n══ FUSION TEST (Ultrasonic → Camera gate) ═══════════")
    print(f"  Camera activates when ultrasonic distance < {HAZARD_DISTANCE_CM} cm")
    print("  Press Ctrl+C to stop.\n")

    usm = UltrasonicManager()
    cam = CameraHazardDetector()

    i = 0
    try:
        while loop_count == 0 or i < loop_count:
            # Step 1: read ultrasonic (fast, always on)
            distance, direction, u_conf = usm.read_all()
            label = DIRECTION_LABELS.get(direction, "?")
            ultrasonic_triggered = (direction != 0 and distance is not None)

            # Step 2: gate the camera
            if ultrasonic_triggered:
                cam_confirmed, cam_conf = cam.check()
                fusion_result = "🚨 REAL HAZARD" if cam_confirmed else "⚠ possible (camera unconfirmed)"
            else:
                cam_confirmed, cam_conf = False, 0.0
                fusion_result = "CLEAR"

            print(
                f"  US:[{label:5s}] {distance or 0:5.1f}cm u_conf={u_conf:.2f} | "
                f"CAM: active={ultrasonic_triggered} cam_conf={cam_conf:.2f} | "
                f"→ {fusion_result}"
            )
            time.sleep(0.15)
            i += 1
    except KeyboardInterrupt:
        print("\n[Test] Stopped by user.")
    finally:
        usm.cleanup()
        cam.shutdown()  # FIX: was cam.stop() — method is called shutdown()


# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sensor test runner")
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ultrasonic", action="store_true", help="Test ultrasonic sensors only")
    group.add_argument("--camera",     action="store_true", help="Test camera only")
    group.add_argument("--both",       action="store_true", help="Test ultrasonic + camera fusion")
    parser.add_argument("--count", type=int, default=0,
                        help="Number of readings (0 = run forever)")
    args = parser.parse_args()

    if args.ultrasonic:
        test_ultrasonic(args.count)
    elif args.camera:
        test_camera(args.count)
    else:
        test_fusion(args.count)