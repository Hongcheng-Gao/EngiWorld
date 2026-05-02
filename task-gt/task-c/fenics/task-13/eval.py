#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


FLOAT_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?(?![A-Za-z0-9_])")


def is_result_artifact(path: Path) -> bool:
    name = path.name.lower()
    return (
        any(k in name for k in ("summary", "result", "report", "diagnosis"))
        or path.suffix.lower() in {".txt", ".csv", ".xy", ".result"}
    )


def is_nonempty_file(path: Path) -> bool:
    if not is_result_artifact(path):
        return True
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
    required = [
        "re_100.py",
        "re_400.py",
        "re_1000.py",
        "summarize.py",
        "summary.txt",
    ]
    for rel in required:
        if not is_nonempty_file(root / rel):
            return False

    results: dict[int, float] = {}
    for raw_line in read_text(root / "summary.txt").splitlines():
        line = raw_line.strip()
        if (not line) or line.startswith("#"):
            continue
        vals = parse_floats(line)
        if len(vals) < 2:
            continue
        re_float, ux = vals[0], vals[1]
        re_int = int(round(re_float))
        if abs(re_float - re_int) > 1e-6:
            continue
        results[re_int] = ux

    for re_val in (100, 400, 1000):
        if re_val not in results:
            return False

    if not (-0.15 <= results[1000] <= 0.0):
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
    print("true" if result == 1 else "false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
