from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent


def main():
    for job in ("job_a", "job_b"):
        subprocess.run([sys.executable, str(ROOT / (job + ".py"))], cwd=ROOT, check=True)
        for suffix in (".xdmf", ".h5", "_metrics.json"):
            output = ROOT / (job + suffix)
            if not output.is_file() or output.stat().st_size == 0:
                raise RuntimeError("Missing solver output: " + str(output))


if __name__ == "__main__":
    main()
