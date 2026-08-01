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


def parse_report(path: Path) -> dict[str, object]:
    data: dict[str, object] = {}
    for raw_line in read_text(path).splitlines():
        line = raw_line.strip()
        if (not line) or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 3 and parts[0] in ("job_a", "job_b"):
            vals_1 = parse_floats(parts[1])
            vals_2 = parse_floats(parts[2])
            if vals_1 and vals_2:
                data[parts[0]] = (vals_1[0], vals_2[0])
            continue
        if len(parts) >= 2 and parts[0] in ("Ratio_Mises", "Ratio_Displacement"):
            vals = parse_floats(parts[1])
            if vals:
                data[parts[0]] = vals[0]
    return data


def check_task(root: Path) -> bool:
    required = [
        "run_pipeline.py",
        "compare.py",
        "job_a.xdmf",
        "job_b.xdmf",
        "job_a_metrics.json",
        "job_b_metrics.json",
        "comparison_report.txt",
    ]
    for rel in required:
        if not is_nonempty_file(root / rel):
            return False

    data = parse_report(root / "comparison_report.txt")
    if "job_a" not in data or "job_b" not in data:
        return False

    mises_a, uy_a = data["job_a"]
    mises_b, uy_b = data["job_b"]

    metrics_a = json.loads(read_text(root / "job_a_metrics.json"))
    metrics_b = json.loads(read_text(root / "job_b_metrics.json"))
    if abs(mises_a - float(metrics_a["max_mises_mpa"])) > 1e-6 * max(1.0, abs(mises_a)):
        return False
    if abs(uy_a - float(metrics_a["tip_uy_mm"])) > 1e-6 * max(1.0, abs(uy_a)):
        return False
    if abs(mises_b - float(metrics_b["max_mises_mpa"])) > 1e-6 * max(1.0, abs(mises_b)):
        return False
    if abs(uy_b - float(metrics_b["tip_uy_mm"])) > 1e-6 * max(1.0, abs(uy_b)):
        return False

    if not (mises_a > 0.0 and mises_b > mises_a and uy_a < 0.0 and uy_b < uy_a):
        return False

    if "Ratio_Mises" not in data or abs(float(data["Ratio_Mises"]) - 2.0) > 0.02:
        return False
    if "Ratio_Displacement" not in data or abs(float(data["Ratio_Displacement"]) - 2.0) > 0.02:
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
