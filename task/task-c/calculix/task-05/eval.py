#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


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


def parse_csv_values(path: Path) -> list[str]:
    content = read_text(path).strip()
    if not content:
        return []
    return [p.strip() for p in content.split(",")]


def write_result(path: Path, value: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"result": int(1 if value else 0)}, ensure_ascii=False) + "\n", encoding="utf-8")


def check_task(root: Path) -> bool:
    required = ["equation.inp", "equation.dat", "summary.txt"]
    for rel in required:
        if not is_nonempty_file(root / rel):
            return False

    parts = parse_csv_values(root / "summary.txt")
    if len(parts) < 5:
        return False

    try:
        uy2 = float(parts[0])
        uy3 = float(parts[1])
        uy6 = float(parts[2])
        uy7 = float(parts[3])
        mises = float(parts[4])
    except (TypeError, ValueError):
        return False

    uys = [uy2, uy3, uy6, uy7]
    if max(abs(v) for v in uys) <= 1e-6:
        return False
    if max(uys) - min(uys) > 1e-5:
        return False
    if mises <= 0:
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
