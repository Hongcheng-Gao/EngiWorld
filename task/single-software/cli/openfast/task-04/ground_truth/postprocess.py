#!/usr/bin/env python3
from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent
ROW = re.compile(r"^\s*(\d+)\s+.*?\s+[FT]\s+\d+\s+(.*)$")


def parse_linear_model(path: Path) -> tuple[np.ndarray, dict[str, int]]:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    state_indices: dict[str, int] = {}
    in_states = False
    for line in lines:
        if line.strip() == "Order of continuous states:":
            in_states = True
            continue
        if in_states and line.strip() == "Order of continuous state derivatives:":
            break
        if not in_states:
            continue
        match = ROW.match(line)
        if not match:
            continue
        description = match.group(2).lower()
        if "first time derivative" in description:
            continue
        if "1st tower fore-aft bending mode dof" in description:
            state_indices["fa"] = int(match.group(1)) - 1
        elif "1st tower side-to-side bending mode dof" in description:
            state_indices["ss"] = int(match.group(1)) - 1

    header_index = next(
        index for index, line in enumerate(lines) if re.fullmatch(r"\s*A:\s*\d+\s*x\s*\d+\s*", line)
    )
    dimensions = [int(value) for value in re.findall(r"\d+", lines[header_index])]
    if len(dimensions) != 2 or dimensions[0] != dimensions[1]:
        raise ValueError("A matrix is not square")
    size = dimensions[0]
    matrix = np.array(
        [[float(value) for value in lines[header_index + row + 1].split()] for row in range(size)],
        dtype=float,
    )
    if matrix.shape != (size, size) or set(state_indices) != {"fa", "ss"}:
        raise ValueError("linear model does not contain the two requested tower states")
    return matrix, state_indices


def modal_frequencies(matrix: np.ndarray, state_indices: dict[str, int]) -> dict[str, float]:
    eigenvalues, eigenvectors = np.linalg.eig(matrix)
    positive_modes = [index for index, value in enumerate(eigenvalues) if value.imag > 1e-8]
    if len(positive_modes) != 2:
        raise ValueError("expected two oscillatory modes")

    result: dict[str, float] = {}
    for mode_index in positive_modes:
        participation = {
            name: abs(eigenvectors[state_index, mode_index])
            for name, state_index in state_indices.items()
        }
        label = max(participation, key=participation.get)
        if label in result:
            raise ValueError("tower modes could not be distinguished")
        result[label] = abs(eigenvalues[mode_index].imag) / (2.0 * math.pi)
    if set(result) != {"fa", "ss"}:
        raise ValueError("missing tower mode")
    return result


def main() -> int:
    matrix, state_indices = parse_linear_model(ROOT / "linear.1.lin")
    frequencies = modal_frequencies(matrix, state_indices)
    (ROOT / "summary.txt").write_text(
        f"{frequencies['fa']:.6f},{frequencies['ss']:.6f}\n", encoding="ascii"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
