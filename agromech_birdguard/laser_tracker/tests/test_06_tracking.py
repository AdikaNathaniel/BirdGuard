import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from main import run

TEST_TARGET = "person"
TEST_CONFIDENCE = 0.3   # accept weaker detections while testing
# Never fire the laser while tracking people -- it aims at the body/face.
# Set True only with a non-person target (e.g. "backpack", "cup", "bottle").
TEST_FIRE_LASER = TEST_TARGET != "person"

if __name__ == "__main__":
    print(f"Tracking target: {TEST_TARGET} | laser {'ENABLED' if TEST_FIRE_LASER else 'DISABLED'}")
    run(target_class=TEST_TARGET, confidence=TEST_CONFIDENCE, fire_laser=TEST_FIRE_LASER)
print("Tracking test done.")
