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
    required = ["rigid.inp", "rigid.dat", "summary.txt"]
    for rel in required:
        if not is_nonempty_file(root / rel):
            return False

    parts = parse_csv_values(root / "summary.txt")
    if len(parts) < 3:
        return False

    try:
        ref_uy = float(parts[0])
        max_node_uy = float(parts[1])
        min_node_uy = float(parts[2])
    except (TypeError, ValueError):
        return False

    tol = 1e-4
    if abs(ref_uy) <= 0.001:
        return False
    if abs(max_node_uy - min_node_uy) > tol:
        return False
    if abs(ref_uy - max_node_uy) > tol:
        return False
    if abs(ref_uy - min_node_uy) > tol:
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
