import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from main import run

if __name__ == "__main__":
    run()
print("Tracking test done.")