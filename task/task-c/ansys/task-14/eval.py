#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def is_result_artifact(path: Path) -> bool:
    name = path.name.lower()
    return (
        any(k in name for k in ("summary", "result", "report", "diagnosis"))
        or path.suffix.lower() in {".txt", ".csv", ".xy", ".result"}
    )


def is_file(path: Path) -> bool:
    if not is_result_artifact(path):
        return True
    return path.exists() and path.is_file()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

FLOAT_RE = re.compile(r"(?<![A-Za-z0-9_])[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")
SEP_RE = re.compile(r"[,\t;，；]+")


def parse_floats(text: str) -> list[float]:
    values: list[float] = []
    for token in FLOAT_RE.findall(text):
        try:
            values.append(float(token))
        except (TypeError, ValueError):
            continue
    return values


def split_fields(line: str) -> list[str]:
    return [p.strip() for p in SEP_RE.split(line) if p.strip()]


def parse_line_numbers(line: str, expected_len: int) -> list[float]:
    values: list[float] = []
    for field in split_fields(line):
        nums = parse_floats(field)
        if nums:
            values.append(nums[-1])
        if len(values) >= expected_len:
            return values[:expected_len]
    fallback = parse_floats(line)
    if len(fallback) >= expected_len:
        return fallback[:expected_len]
    return values


def write_result(path: Path, value: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"result": int(1 if value else 0)}, ensure_ascii=False) + "\n", encoding="utf-8")


def check_task(root: Path) -> bool:
    required = ["channel.jou", "outlet_profile.xy"]
    for rel in required:
        if not is_file(root / rel):
            return False

    lines = read_text(root / "outlet_profile.xy").splitlines()
    velocities = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("("):
            continue
        nums = parse_line_numbers(line, 2)
        if len(nums) >= 2:
            velocities.append(nums[1])

    if not velocities:
        return False

    u_max = max(velocities)
    u_min = min(velocities)
    if abs(u_max - 0.03) / 0.03 > 0.10:
        return False
    if abs(u_min) > 0.001:
        return False

    return True

def evaluate() -> int:
    root = Path(r"C:\\Users\\Administrator\\Desktop")
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
