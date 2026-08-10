from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


TARGETS = [
    ("SIG", 0.15),
    ("PWR", 0.40),
    ("HSPEED", 0.20),
]

EXPECTED_NET_CLASSES = {
    "SIG": {"N$1", "N$2", "N$3", "N$4"},
    "PWR": {"GND", "VCC", "+12V"},
    "HSPEED": {"A0", "A1", "A2", "A3", "A4", "B0", "B1", "B2", "B3", "B4", "B5", "B6", "B7"},
}


def _parse_width_mm(value: str | None) -> float | None:
    if value is None:
        return None
    s = value.strip().lower()
    try:
        if s.endswith("mm"):
            return float(s[:-2])
        if s.endswith("um"):
            return float(s[:-2]) / 1000.0
        if s.endswith("mil"):
            return float(s[:-3]) * 0.0254
        if s.endswith("inch"):
            return float(s[:-4]) * 25.4
        return float(s)
    except ValueError:
        return None


def evaluate(submission_dir: str) -> bool:
    sub = Path(submission_dir).resolve()
    target = None
    for name in ("classed.sch", "answer.sch"):
        cand = sub / name
        if cand.exists():
            target = cand
            break
    if target is None:
        return False

    try:
        root = ET.parse(target).getroot()
    except Exception:
        return False

    eval_dir = Path(__file__).resolve().parent
    starter_path = next(
        (path for path in (eval_dir / "board.sch", eval_dir / "init_file" / "board.sch") if path.exists()),
        eval_dir / "board.sch",
    )
    starter = ET.parse(starter_path).getroot()
    classes = {c.get("name"): c for c in root.iter("class") if c.get("name")}
    if not {"default", "SIG", "PWR", "HSPEED"}.issubset(classes):
        return False
    for name, want in TARGETS:
        c = classes.get(name)
        if c is None or c.get("number") is None:
            return False
        width = _parse_width_mm(c.get("width"))
        if width is None or abs(width - want) > 0.005:
            return False

    numbers = [classes[name].get("number") for name, _ in TARGETS]
    if len(set(numbers)) != 3:
        return False
    if classes["SIG"].get("number") == "0" or classes["PWR"].get("number") == "0" or classes["HSPEED"].get("number") == "0":
        return False

    nets = {n.get("name"): n.get("class") for n in root.findall(".//net") if n.get("name")}
    for cls_name, net_names in EXPECTED_NET_CLASSES.items():
        number = classes[cls_name].get("number")
        for net_name in net_names:
            if nets.get(net_name) != number:
                return False

    starter_nets = {n.get("name"): n.get("class") for n in starter.findall(".//net") if n.get("name")}
    for net_name, starter_class in starter_nets.items():
        if net_name not in nets:
            return False
        if net_name not in {"N$1", "N$2", "N$3", "N$4", "GND", "VCC", "+12V", "A0", "A1", "A2", "A3", "A4", "B0", "B1", "B2", "B3", "B4", "B5", "B6", "B7"}:
            if nets[net_name] != starter_class:
                return False
    return True


def main(argv: list[str]) -> int:
    if len(argv) > 2:
        print("usage: python eval.py SUBMISSION_DIR", file=sys.stderr)
        return 2
    submission_dir = argv[1] if len(argv) == 2 else Path(__file__).resolve().parent
    ok = evaluate(submission_dir)
    print("True" if ok else "False")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
