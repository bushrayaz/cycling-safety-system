"""
test_camera_integration.py
--------------------------
Step-by-step integration test for the Raspberry Pi AI Camera (IMX500).

Run each step individually to isolate exactly where any issue is.

Usage (on the Pi):
    cd cycling-safety-system/firmware/src
    python3 tests/test_camera_integration.py --step 1   # check camera detected
    python3 tests/test_camera_integration.py --step 2   # take a test photo
    python3 tests/test_camera_integration.py --step 3   # test picamera2 library
    python3 tests/test_camera_integration.py --step 4   # test full camera.py module
    python3 tests/test_camera_integration.py --step 5   # live hazard detection loop

Press Ctrl+C to stop any running step.
"""

import sys
import time
import argparse
import subprocess

sys.path.insert(0, ".")


# ─────────────────────────────────────────────────────────────────
def step1_check_camera_detected():
    """
    Step 1: Check if the Pi can physically see the IMX500 camera.
    This must pass before anything else will work.
    """
    print("\n══ STEP 1: Check camera is detected ════════════════")
    result = subprocess.run(
        ["rpicam-still", "--list-cameras"],
        capture_output=True,
        text=True
    )
    output = result.stdout + result.stderr
    print(output)

    if "imx500" in output.lower() or "available" in output.lower() and "no cameras" not in output.lower():
        print("✅ PASS — Camera detected!")
    else:
        print("❌ FAIL — No camera detected.")
        print("\nTry these fixes:")
        print("  1. sudo apt install imx500-all -y")
        print("  2. sudo reboot")
        print("  3. Check ribbon cable is firmly connected to CAM/DISP 0")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────
def step2_take_test_photo():
    """
    Step 2: Take a test photo using rpicam-still.
    Confirms the camera hardware is fully working.
    """
    print("\n══ STEP 2: Take a test photo ════════════════════════")
    print("  Taking photo → /home/bike/test.jpg ...")

    result = subprocess.run(
        ["rpicam-still", "-o", "/home/bike/test.jpg", "--timeout", "2000"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("✅ PASS — Photo saved to /home/bike/test.jpg")
        print("  View it via Raspberry Pi Connect file manager to confirm.")
    else:
        print("❌ FAIL — Could not take photo.")
        print(result.stderr)
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────
def step3_test_picamera2():
    """
    Step 3: Test that picamera2 Python library works.
    Captures one frame and checks its shape.
    """
    print("\n══ STEP 3: Test picamera2 library ══════════════════")
    try:
        from picamera2 import Picamera2
        print("  picamera2 imported successfully.")

        cam = Picamera2()
        config = cam.create_preview_configuration(
            main={"format": "RGB888", "size": (640, 480)}
        )
        cam.configure(config)
        cam.start()
        time.sleep(1)

        frame = cam.capture_array()
        cam.stop()

        print(f"  Frame captured — shape: {frame.shape}")

        if frame.shape == (480, 640, 3):
            print("✅ PASS — picamera2 is working correctly!")
        else:
            print(f"⚠️  WARNING — Unexpected frame shape: {frame.shape}")

    except ImportError:
        print("❌ FAIL — picamera2 not installed.")
        print("  Run: sudo apt install python3-picamera2 -y")
        sys.exit(1)
    except Exception as e:
        print(f"❌ FAIL — {e}")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────
def step4_test_camera_module():
    """
    Step 4: Test the full camera.py module.
    Initialises CameraHazardDetector and runs one check() call.
    """
    print("\n══ STEP 4: Test camera.py module ════════════════════")
    try:
        from sensors.camera import CameraHazardDetector
        print("  Importing CameraHazardDetector...")

        cam = CameraHazardDetector()
        print("  Running one check()...")

        confirmed, conf = cam.check()
        print(f"  Result → confirmed={confirmed}, confidence={conf:.3f}")

        cam.shutdown()

        print("✅ PASS — camera.py module working!")
        print("  Note: confirmed=False is expected — no YOLO model loaded yet.")

    except Exception as e:
        print(f"❌ FAIL — {e}")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────
def step5_live_detection(loop_count: int = 0):
    """
    Step 5: Live hazard detection loop.
    Runs camera continuously and prints results.
    Only useful once YOLO model is trained and loaded.
    """
    print("\n══ STEP 5: Live detection loop ══════════════════════")
    print("  Watching for: car, truck, bus, pedestrian, bicycle")
    print("  Press Ctrl+C to stop.\n")

    from sensors.camera import CameraHazardDetector
    cam = CameraHazardDetector()

    i = 0
    try:
        while loop_count == 0 or i < loop_count:
            confirmed, conf = cam.check()
            status = "🚨 HAZARD CONFIRMED" if confirmed else "clear"
            print(f"  Frame {i+1:04d} → confirmed={confirmed}  confidence={conf:.3f}  [{status}]")
            time.sleep(0.2)
            i += 1
    except KeyboardInterrupt:
        print("\n[Test] Stopped by user.")
    finally:
        cam.shutdown()


# ─────────────────────────────────────────────────────────────────
STEPS = {
    1: step1_check_camera_detected,
    2: step2_take_test_photo,
    3: step3_test_picamera2,
    4: step4_test_camera_module,
    5: step5_live_detection,
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Camera integration test")
    parser.add_argument("--step", type=int, choices=[1, 2, 3, 4, 5], required=True,
                        help="Which step to run (1-5)")
    parser.add_argument("--count", type=int, default=0,
                        help="Number of frames for step 5 (0 = run forever)")
    args = parser.parse_args()

    print(f"\n[Integration Test] Running Step {args.step}...")
    if args.step == 5:
        STEPS[args.step](args.count)
    else:
        STEPS[args.step]()
    print("\n[Integration Test] Done.")