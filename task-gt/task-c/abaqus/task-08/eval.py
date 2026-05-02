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


def parse_number_from_field(field: str) -> float:
    vals = parse_floats(field)
    if not vals:
        raise ValueError(f"no float in field: {field!r}")
    return vals[-1]


def parse_data_lines(path: Path) -> list[str]:
    lines: list[str] = []
    for raw in read_text(path).splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        lines.append(line)
    return lines


def parse_last_data_fields(path: Path, min_fields: int) -> list[str] | None:
    for line in reversed(parse_data_lines(path)):
        fields = split_fields(line)
        if len(fields) >= min_fields:
            return fields
    return None


def parse_summary_values(path: Path, expected_len: int) -> list[float] | None:
    for line in reversed(parse_data_lines(path)):
        vals: list[float] = []
        for field in split_fields(line):
            try:
                vals.append(parse_number_from_field(field))
            except ValueError:
                continue
        if len(vals) >= expected_len:
            return vals[:expected_len]

    all_vals = parse_floats(read_text(path))
    if len(all_vals) >= expected_len:
        return all_vals[-expected_len:]
    return None




def write_result(path: Path, value: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"result": int(1 if value else 0)}, ensure_ascii=False) + "\n", encoding="utf-8")


def check_task(root: Path) -> bool:
    jobs = ["torsion_500", "torsion_1000", "torsion_1500"]
    for job in jobs:
        if not is_file(root / f"{job}.inp") or not is_file(root / f"{job}.odb"):
            return False
    if not is_file(root / "summary.txt"):
        return False

    lines = read_text(root / "summary.txt").splitlines()
    results = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = split_fields(line)
        if len(parts) >= 3:
            try:
                results[parts[0]] = (parse_number_from_field(parts[1]), parse_number_from_field(parts[2]))
            except (TypeError, ValueError):
                continue

    if len(results) < 3:
        numeric_rows = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            vals = []
            for field in split_fields(line):
                try:
                    vals.append(parse_number_from_field(field))
                except (TypeError, ValueError):
                    continue
            if len(vals) >= 3:
                numeric_rows.append(vals)
        for vals in numeric_rows:
            torque = int(round(vals[0]))
            if torque == 500:
                results["torsion_500"] = (vals[1], vals[2])
            elif torque == 1000:
                results["torsion_1000"] = (vals[1], vals[2])
            elif torque == 1500:
                results["torsion_1500"] = (vals[1], vals[2])

    if len(results) < 3:
        return False

    expected = {
        "torsion_500": (2.55, 0.000631),
        "torsion_1000": (5.09, 0.001261),
        "torsion_1500": (7.64, 0.001892),
    }

    for job, pair in expected.items():
        exp_mises, exp_rot = pair
        if job not in results:
            return False
        mises, rot = results[job]
        if abs(mises - exp_mises) / exp_mises > 0.05:
            return False
        if abs(abs(rot) - exp_rot) / exp_rot > 0.05:
            return False

    mises_vals = [results[j][0] for j in jobs]
    rot_vals = [abs(results[j][1]) for j in jobs]
    if not all(mises_vals[i] < mises_vals[i + 1] for i in range(2)):
        return False
    if not all(rot_vals[i] < rot_vals[i + 1] for i in range(2)):
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
