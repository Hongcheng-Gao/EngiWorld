"""Sync config.launch.command with [Software] path in instruction for task-c ansys."""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "task" / "task-c" / "ansys"

SOFTWARE_RE = re.compile(r"\[Software\][^\`]*\`([^\`]+)\`", re.I)


def parse_software_cmd(text: str) -> list[str]:
    text = text.strip()
    for suffix in (" (adjust path to your install).", " (version/path may differ on your machine)."):
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()
    for ext in (".exe", ".bat"):
        idx = text.lower().find(ext)
        if idx != -1:
            exe = text[: idx + len(ext)]
            rest = text[idx + len(ext) :].strip()
            if rest:
                return [exe] + rest.split()
            return [exe]
    return [text]


def main() -> None:
    for jpath in sorted(ROOT.glob("task-*/task-*.json")):
        obj = json.loads(jpath.read_text(encoding="utf-8"))
        m = SOFTWARE_RE.search(obj.get("instruction", ""))
        if not m:
            continue
        cmd = parse_software_cmd(m.group(1))
        for c in obj.get("config", []):
            if c.get("type") == "launch":
                c["parameters"]["command"] = cmd
                jpath.write_text(
                    json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                print("synced", jpath.relative_to(REPO), "->", cmd)


if __name__ == "__main__":
    main()
