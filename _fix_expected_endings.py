"""Replace evaluator.expected.rules.expected '\\r\\n' tails with '\\n'.

The osworld /run/command HTTP API normalises stdout line endings to '\\n',
so a CRLF expected can never match no matter what the eval prints.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOTS = [
    Path(r"d:/research/project-engiworld/Engiworld/task/task-c"),
    Path(r"d:/research/project-engiworld/Engiworld/task/task-v"),
    Path(r"d:/research/project-engiworld/Engiworld/task-gt/task-c"),
    Path(r"d:/research/project-engiworld/Engiworld/task-gt/task-v"),
]


def fix_expected(node) -> bool:
    if isinstance(node, dict):
        rules = node.get("rules")
        if isinstance(rules, dict):
            v = rules.get("expected")
            if isinstance(v, str) and "\r\n" in v:
                rules["expected"] = v.replace("\r\n", "\n")
                return True
        any_changed = False
        for k, val in node.items():
            if fix_expected(val):
                any_changed = True
        return any_changed
    if isinstance(node, list):
        any_changed = False
        for v in node:
            if fix_expected(v):
                any_changed = True
        return any_changed
    return False


def main() -> None:
    grand_files = 0
    for root in ROOTS:
        bucket = f"{root.parent.name}/{root.name}"
        json_files = [j for j in root.rglob("task-*.json") if j.parent.name.startswith("task-")]
        files_changed = 0
        for jf in json_files:
            try:
                data = json.loads(jf.read_text(encoding="utf-8"))
            except Exception:
                continue
            if fix_expected(data):
                txt = json.dumps(data, indent=2, ensure_ascii=False)
                if not txt.endswith("\n"):
                    txt += "\n"
                jf.write_text(txt, encoding="utf-8")
                files_changed += 1
        print(f"{bucket}: {files_changed}/{len(json_files)} files updated")
        grand_files += files_changed
    print(f"\nTotal: {grand_files} files updated.")


if __name__ == "__main__":
    main()
