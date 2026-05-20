import subprocess, sys

if __name__ == "__main__":
    subprocess.run([sys.executable, "job_baseline.py"], check=True)
    subprocess.run([sys.executable, "job_yaw.py"], check=True)
