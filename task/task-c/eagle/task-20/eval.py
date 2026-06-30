from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from pathlib import Path


STARTER_BRD = Path(__file__).resolve().parent / "init_file" / "dense.brd"
TARGET_COUNT = 5


def _elements(root: ET.Element) -> list[ET.Element]:
    return root.findall(".//elements/element")


def _plain_texts_l25(root: ET.Element) -> list[ET.Element]:
    plain = root.find(".//board/plain")
    if plain is None:
        return []
    return [t for t in plain.findall("text") if t.get("layer") == "25"]


def _centroid(elements: list[ET.Element]) -> tuple[float, float]:
    xs = [float(e.get("x", "0")) for e in elements]
    ys = [float(e.get("y", "0")) for e in elements]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def _target_names(elements: list[ET.Element]) -> set[str]:
    cx, cy = _centroid(elements)
    ranked = sorted(
        (e for e in elements if e.get("name")),
        key=lambda e: math.hypot(float(e.get("x", "0")) - cx, float(e.get("y", "0")) - cy),
    )
    return {e.get("name") for e in ranked[:TARGET_COUNT] if e.get("name")}


def evaluate(submission_dir: str) -> bool:
    sub = Path(submission_dir).resolve()
    target = None
    for name in ("labeled.brd", "answer.brd"):
        p = sub / name
        if p.exists():
            target = p
            break
    if target is None or not STARTER_BRD.exists():
        return False

    try:
        starter = ET.parse(STARTER_BRD).getroot()
        root = ET.parse(target).getroot()
    except Exception:
        return False

    starter_elems = _elements(starter)
    out_elems = _elements(root)
    starter_names = {e.get("name") for e in starter_elems if e.get("name")}
    out_names = {e.get("name") for e in out_elems if e.get("name")}

    if len(out_elems) != len(starter_elems):
        return False
    if starter_names != out_names:
        return False

    texts = _plain_texts_l25(root)
    labels = [(t.text or "").strip() for t in texts]
    chosen = _target_names(starter_elems)

    if len(texts) != TARGET_COUNT or set(labels) != chosen or len(labels) != len(set(labels)):
        return False
    if not all(label in starter_names for label in labels):
        return False

    starter_by_name = {e.get("name"): e for e in starter_elems if e.get("name")}
    for t in texts:
        label = (t.text or "").strip()
        ref = starter_by_name.get(label)
        if ref is None:
            return False
        tx = float(t.get("x", "nan"))
        ty = float(t.get("y", "nan"))
        rx = float(ref.get("x", "nan"))
        ry = float(ref.get("y", "nan"))
        if math.hypot(tx - rx, ty - ry) > 2.0:
            return False

    return True


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("usage: python eval.py SUBMISSION_DIR", file=sys.stderr)
        sys.exit(2)
    print("True" if evaluate(sys.argv[1]) else "False")
