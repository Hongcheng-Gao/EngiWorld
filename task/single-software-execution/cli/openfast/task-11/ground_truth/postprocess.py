#!/usr/bin/env python3
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parent
lines = (root / "blade_mode.1.BD1.lin").read_text(errors="replace").splitlines()
count = int(next(line.split(":", 1)[1] for line in lines if "Number of continuous states:" in line))
matrix_start = next(i for i, line in enumerate(lines) if line.startswith("A:")) + 1
matrix = np.array([[float(value) for value in line.split()] for line in lines[matrix_start:matrix_start + count]])
if matrix.shape != (count, count):
    raise RuntimeError("incomplete A matrix")
frequencies = sorted(value.imag / (2 * np.pi) for value in np.linalg.eigvals(matrix) if value.imag > 1e-6)
(root / "summary.txt").write_text(f"{frequencies[0]:.6f}, {frequencies[1]:.6f}\n")
