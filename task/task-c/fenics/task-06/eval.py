#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import math
import re
import subprocess
import sys
from pathlib import Path


FLOAT_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?(?![A-Za-z0-9_])")


def is_result_artifact(path: Path) -> bool:
    name = path.name.lower()
    return (
        any(k in name for k in ("summary", "result", "report", "diagnosis"))
        or path.suffix.lower() in {".txt", ".csv", ".xy", ".result"}
    )


def is_nonempty_file(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def parse_floats(text: str) -> list[float]:
    out: list[float] = []
    for token in FLOAT_RE.findall(text):
        try:
            out.append(float(token))
        except (TypeError, ValueError):
            continue
    return out


def write_result(path: Path, value: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"result": int(1 if value else 0)}, ensure_ascii=False) + "\n", encoding="utf-8")


def check_task(root: Path) -> bool:
    required = ["nonlinear.py", "summary.txt"]
    for rel in required:
        if not is_nonempty_file(root / rel):
            return False

    script = root / "nonlinear.py"
    source = read_text(script)
    try:
        ast.parse(source, filename=str(script))
    except SyntaxError:
        return False
    normalized = re.sub(r"\s+", "", source)
    required_code = ("fromdolfinimport", "(1+u**2)*inner(grad(u),grad(v))*dx", "Constant(1.0)", "NonlinearVariationalProblem(", "relative_tolerance", "1e-6")
    if any(fragment not in normalized for fragment in required_code):
        return False

    summary = root / "summary.txt"
    summary.unlink(missing_ok=True)
    try:
        completed = subprocess.run(
            [sys.executable, str(script)], cwd=root, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, timeout=120, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    if completed.returncode != 0 or not is_nonempty_file(summary):
        return False

    vals = parse_floats(read_text(summary))
    if len(vals) != 2 or not all(math.isfinite(value) for value in vals):
        return False
    center, mx = vals[0], vals[1]

    if abs(center - 0.073539) > 0.005:
        return False
    if abs(mx - 0.073539) > 0.005 or abs(mx - center) > 0.002:
        return False
    return True

def evaluate() -> int:
    root = Path("/home/user/Desktop")
    try:
        ok = check_task(root)
    except Exception:
        ok = False
    return 1 if ok else 0


def main() -> int:
    result = evaluate()
    print("True" if result == 1 else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
