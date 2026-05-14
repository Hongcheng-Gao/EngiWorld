#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

NUMBER_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?$")


def is_result_artifact(path: Path) -> bool:
    name = path.name.lower()
    return (
        any(k in name for k in ("summary", "result", "report", "diagnosis"))
        or path.suffix.lower() in {".txt", ".csv", ".xy", ".result"}
    )


def is_nonempty_file(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    if not is_result_artifact(path):
        return True
    return path.stat().st_size > 0


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def parse_number(token: str) -> float:
    s = token.strip()
    if not NUMBER_RE.fullmatch(s):
        raise ValueError(f"not a plain float token: {token!r}")
    return float(s)


def parse_single_line_csv_numbers(path: Path, expected_len: int) -> list[float]:
    lines = [
        ln.strip()
        for ln in read_text(path).splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    ]
    if len(lines) != 1:
        raise ValueError("summary must contain exactly one non-comment data line")
    parts = [p.strip() for p in lines[0].split(",")]
    if len(parts) != expected_len:
        raise ValueError(f"expected {expected_len} columns, got {len(parts)}")
    return [parse_number(p) for p in parts]


def check_required_files(root: Path, required: list[str]) -> bool:
    for rel in required:
        if not is_nonempty_file(root / rel):
            return False
    return True


def write_result(path: Path, value: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"result": int(1 if value else 0)}, ensure_ascii=False) + "\n", encoding="utf-8")


def close_enough(a: float, b: float, tol: float = 1e-3) -> bool:
    return abs(a - b) <= tol

def check_task(root: Path) -> bool:
    required = [
        "shockTube/0/p",
        "shockTube/0/T",
        "shockTube/0/U",
        "shockTube/constant/thermophysicalProperties",
        "shockTube/system/controlDict",
        "summary.txt",
    ]
    if not check_required_files(root, required):
        return False

    values = parse_single_line_csv_numbers(root / "summary.txt", 1)
    target = [28477.862667]
    return all(close_enough(v, t) for v, t in zip(values, target))

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
