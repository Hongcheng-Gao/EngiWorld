#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

EXPECTED_TEXT = "Diagnosis report generated from runtime logs.\n\nObserved issues:\n\nFix attempts:\n1) Rebuilt preprocessing mesh and decomposition.\n2) Re-ran initializer/solver chain with available binaries.\n3) Captured missing executable/dependency indicators for remediation.\n\nOutcome: averaged/postprocessing artifacts may be incomplete when solver binaries are missing in current environment.\n"


def is_nonempty_file(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.strip() for ln in text.split("\n")]
    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def write_result(path: Path, value: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"result": int(1 if value else 0)}, ensure_ascii=False) + "\n", encoding="utf-8")


def check_task(root: Path) -> bool:
    diagnosis_path = root / "diagnosis.txt"
    if not is_nonempty_file(diagnosis_path):
        return False
    actual = normalize_text(read_text(diagnosis_path))
    expected = normalize_text(EXPECTED_TEXT)
    return actual == expected


def evaluate() -> int:
    root = Path("/home/user/Desktop")
    try:
        ok = check_task(root)
    except Exception:
        ok = False
    write_result(root / "eval.json", 1 if ok else 0)
    return 1 if ok else 0


def main() -> int:
    result = evaluate()
    print("True" if result == 1 else "False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
