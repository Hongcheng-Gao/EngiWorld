"""Normalize backslashes in `local_path` (and `trajectory`) fields of every
task-XX.json under task/ and task-gt/.

We deliberately leave `path` (the VM target path, e.g.
`C:\\Users\\Administrator\\Desktop\\foo.dxf`) untouched, since those are the
real Windows-VM destinations that the upload step writes to.
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


def fix(node, changed: list[str]) -> bool:
    """Walk `node`, normalize backslashes in `local_path`/`trajectory`. Return True if mutated."""
    mutated = False
    if isinstance(node, dict):
        for key in ("local_path", "trajectory"):
            v = node.get(key)
            if isinstance(v, str) and "\\" in v:
                new_v = v.replace("\\", "/")
                node[key] = new_v
                changed.append(f"  {key}: {v!r} -> {new_v!r}")
                mutated = True
        for v in node.values():
            if fix(v, changed):
                mutated = True
    elif isinstance(node, list):
        for v in node:
            if fix(v, changed):
                mutated = True
    return mutated


def main() -> None:
    grand_files = 0
    grand_changes = 0
    for root in ROOTS:
        bucket = f"{root.parent.name}/{root.name}"
        json_files = [j for j in root.rglob("task-*.json") if j.parent.name.startswith("task-")]
        files_changed = 0
        change_count = 0
        for jf in json_files:
            try:
                txt = jf.read_text(encoding="utf-8")
                data = json.loads(txt)
            except Exception as exc:
                print(f"[err] cannot parse {jf}: {exc}")
                continue
            local_changes: list[str] = []
            if fix(data, local_changes):
                # Re-serialize keeping pretty formatting.  Use 2-space indent
                # (matches what the existing files use) and ensure_ascii=False
                # to preserve any unicode.
                new_txt = json.dumps(data, indent=2, ensure_ascii=False)
                if not new_txt.endswith("\n"):
                    new_txt += "\n"
                jf.write_text(new_txt, encoding="utf-8")
                files_changed += 1
                change_count += len(local_changes)
        print(f"{bucket}: {files_changed}/{len(json_files)} files updated, {change_count} fields changed")
        grand_files += files_changed
        grand_changes += change_count

    print(f"\nTotal: {grand_files} files updated, {grand_changes} fields changed.")


if __name__ == "__main__":
    main()
