#!/usr/bin/env python3
"""Align cadence-orcad task-v with harness launch: soften Open-Desktop lines; restore intentional empty launch."""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CAD = REPO / "task" / "task-v" / "cadence-orcad"


def fix_instruction(ins: str) -> str:
    s = ins
    s = re.sub(
        r"^Open `C:\\Users\\User\\Desktop\\(.+?)` in Capture's Part Editor\.\s*",
        r"The library file `\1` is already open in Capture's Part Editor. ",
        s,
        count=1,
    )
    s = re.sub(
        r"^Open `C:\\Users\\User\\Desktop\\(.+?)` in OrCAD Capture ",
        r"The schematic `\1` is already open in OrCAD Capture. ",
        s,
        count=1,
    )
    s = re.sub(
        r"^Open `C:\\Users\\User\\Desktop\\(.+?)` in Capture and ",
        r"The schematic `\1` is already open in OrCAD Capture; ",
        s,
        count=1,
    )
    s = re.sub(
        r"^Open `C:\\Users\\User\\Desktop\\(.+?)` in Capture\.\s*",
        r"The schematic `\1` is already open in OrCAD Capture. ",
        s,
        count=1,
    )
    s = re.sub(
        r"^Open `C:\\Users\\User\\Desktop\\(.+?)` in Allegro PCB Editor,?\s*",
        r"The board `\1` is already open in Allegro PCB Editor. ",
        s,
        count=1,
    )
    return s


def main() -> None:
    n_files = 0
    n_ins = 0
    for jf in sorted(CAD.glob("task-*/task-*.json")):
        raw = jf.read_text(encoding="utf-8")
        data = json.loads(raw)
        changed = False

        ins = data.get("instruction")
        if isinstance(ins, str):
            new_ins = fix_instruction(ins)
            if new_ins != ins:
                data["instruction"] = new_ins
                changed = True
                n_ins += 1

        if jf.parent.name == "task-38":
            for b in data.get("config") or []:
                if b.get("type") == "launch":
                    params = b.setdefault("parameters", {})
                    if params.get("command") != []:
                        params["command"] = []
                        changed = True
                    break

        if changed:
            jf.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            n_files += 1

    print(f"updated {n_files} files ({n_ins} instruction edits)")


if __name__ == "__main__":
    main()
