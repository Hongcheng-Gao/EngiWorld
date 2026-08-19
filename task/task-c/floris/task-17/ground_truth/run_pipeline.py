import subprocess
import sys
from pathlib import Path


def require_output(name):
    path = Path(name)
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"missing or empty output: {name}")

if __name__ == "__main__":
    subprocess.run([sys.executable, "job_baseline.py"], check=True)
    require_output("baseline.csv")
    subprocess.run([sys.executable, "job_yaw.py"], check=True)
    require_output("yaw.csv")
