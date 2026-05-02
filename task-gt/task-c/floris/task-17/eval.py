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
    values: list[float] = []
    for token in FLOAT_RE.findall(text):
        try:
            values.append(float(token))
        except (TypeError, ValueError):
            continue
    return values


def write_result(path: Path, value: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"result": int(1 if value else 0)}, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_report(path: Path) -> dict[str, tuple[float, float] | float]:
    data: dict[str, tuple[float, float] | float] = {}
    for raw_line in read_text(path).splitlines():
        line = raw_line.strip()
        if (not line) or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 3 and parts[0] in ("baseline", "yaw"):
            pair_vals = parse_floats(parts[1]) + parse_floats(parts[2])
            if len(pair_vals) >= 2:
                data[parts[0]] = (pair_vals[0], pair_vals[1])
            continue
        if len(parts) >= 2 and parts[0].startswith("Gain"):
            vals = parse_floats(parts[1])
            if vals:
                data[parts[0]] = vals[0]
    return data


def check_task(root: Path) -> bool:
    required = ["run_pipeline.py", "compare.py", "comparison_report.txt"]
    for rel in required:
        if not is_nonempty_file(root / rel):
            return False

    data = parse_report(root / "comparison_report.txt")
    if "baseline" not in data or "yaw" not in data:
        return False

    base_total, base_down = data["baseline"]  # type: ignore[misc]
    yaw_total, yaw_down = data["yaw"]  # type: ignore[misc]

    if yaw_down <= base_down:
        return False
    if yaw_total <= base_total:
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
