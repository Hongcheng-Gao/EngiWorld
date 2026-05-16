#!/usr/bin/env python3
"""Remove all config blocks with type==launch from task-c/**/task-*.json."""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TASK_C = REPO / "task" / "task-c"


def main() -> None:
    n = 0
    for jf in sorted(TASK_C.rglob("task-*.json")):
        if not jf.name.startswith("task-"):
            continue
        raw = jf.read_text(encoding="utf-8")
        data = json.loads(raw)
        cfg = data.get("config")
        if not isinstance(cfg, list):
            continue
        new_cfg = [b for b in cfg if b.get("type") != "launch"]
        if len(new_cfg) == len(cfg):
            continue
        data["config"] = new_cfg
        jf.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        n += 1
    print(f"removed launch from {n} task-c json files")


if __name__ == "__main__":
    main()
