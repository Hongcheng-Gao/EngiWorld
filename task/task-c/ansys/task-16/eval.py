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


def write_result(path: Path, value: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"result": int(1 if value else 0)}, ensure_ascii=False) + "\n", encoding="utf-8")


def check_task(root: Path) -> bool:
    required = ["pipe.jou", "mass_flow.txt"]
    for rel in required:
        if not is_file(root / rel):
            return False

    content = read_text(root / "mass_flow.txt").strip()
    expected_mdot = 1.96

    try:
        mdot = float(content)
    except (TypeError, ValueError):
        tokens = re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", content)
        if not tokens:
            return False
        values = []
        for token in tokens:
            try:
                values.append(float(token))
            except (TypeError, ValueError):
                continue
        if not values:
            return False
        mdot = min(values, key=lambda x: abs(x - expected_mdot))

    if abs(mdot - expected_mdot) / expected_mdot > 0.10:
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
