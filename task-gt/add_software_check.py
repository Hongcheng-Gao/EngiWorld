"""Wrap each task-c task's `eval.py` with a `check_and_eval.py` smoke-test wrapper.

For every task json under `task-gt/task-c/<app>/<task>/` whose evaluator
calls `python .../eval.py` and expects `True\\r\\n` / `true\\r\\n`, this
script:

1. Generates a per-task `check_and_eval.py` next to the existing `eval.py`.
   The wrapper first runs an app-specific CLI / file-existence check that
   verifies the underlying software is actually usable on the VM. If the
   check fails it prints `False` and exits 0 (so `exact_match` against the
   `True`/`true` ground truth fails clearly with a "software broken"
   reading instead of a regular wrong-answer reading). If the check
   passes it execs the original `eval.py` and forwards its stdout/stderr
   /exit-code byte-for-byte (preserving CRLF on Windows / LF on Linux).
2. Patches the task json to:
   - upload `check_and_eval.py` alongside `eval.py` in
     `evaluator.postconfig`, and
   - change `evaluator.result.command` from `python .../eval.py` to
     `python .../check_and_eval.py`.
   Everything else (`expected`, `func`, `instruction`, `config`,
   per-task `eval.py` itself, ...) is left untouched.

The script is idempotent: re-running it overwrites
`check_and_eval.py` with the current canonical body, deduplicates the
upload entry, and only flips `result.command` if it still points at
`eval.py`.

Usage:
    python add_software_check.py [--dry-run] [--app APP] [--task TASK_DIR]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent / "task-c"


# ---------------------------------------------------------------------------
# Per-app smoke-test specs.
#
# Each entry produces the body of a `check_software()` function inside the
# generated `check_and_eval.py`. The function returns True iff the software
# is "usable" on the VM. Two flavours:
#
#   - file-existence checks: GUI-only Windows apps where we can't drive the
#     CLI without licensing dialogs. We just verify the launcher exe is
#     installed (matches the canonical command list in add_init_launch.py).
#   - subprocess checks: apps with a real headless CLI. We run the canonical
#     CLI command with a generous timeout and require returncode == 0.
#
# Keep these aligned with task-gt/add_init_launch.py so the launch step (run
# during config) and the evaluator check (run during evaluator) probe the
# same thing.
# ---------------------------------------------------------------------------

FILE_EXISTS_CHECK = "file_exists"
SUBPROCESS_CHECK = "subprocess"

CHECK_SPECS: dict[str, dict[str, Any]] = {
    "abaqus": {
        "kind": SUBPROCESS_CHECK,
        "cmd": ["cmd", "/c", "abaqus information=version"],
        "timeout": 180,
        "shell": False,
    },
    "altium-designer": {
        "kind": FILE_EXISTS_CHECK,
        "paths": [r"C:\Program Files\Altium\AD26\X2.EXE"],
    },
    "ansys": {
        "kind": SUBPROCESS_CHECK,
        "cmd": [
            r"C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ansys.exe",
            "-b",
            "-i",
            "nul",
        ],
        "timeout": 180,
        "shell": False,
    },
    "archicad": {
        "kind": FILE_EXISTS_CHECK,
        "paths": [
            r"C:\Users\Administrator\Desktop\Archicad 29\Archicad Starter.exe",
            r"C:\Program Files\Graphisoft\Archicad 27\Archicad Starter.exe",
        ],
        "any": True,
    },
    "autocad": {
        "kind": FILE_EXISTS_CHECK,
        "paths": [r"C:\Program Files\Autodesk\AutoCAD 2027\acad.exe"],
    },
    "bonsai": {
        "kind": SUBPROCESS_CHECK,
        "cmd": [
            "bash",
            "-lc",
            "BLENDER=$(command -v blender 2>/dev/null); "
            "[ -z \"$BLENDER\" ] && [ -x \"$HOME/blender-4.2.0-linux-x64/blender\" ] "
            "&& BLENDER=\"$HOME/blender-4.2.0-linux-x64/blender\"; "
            "[ -z \"$BLENDER\" ] && [ -x \"./blender-4.2.0-linux-x64/blender\" ] "
            "&& BLENDER=\"./blender-4.2.0-linux-x64/blender\"; "
            "[ -z \"$BLENDER\" ] && exit 1; "
            "\"$BLENDER\" --background --python-expr \"import bonsai\" "
            "1>/dev/null 2>&1",
        ],
        "timeout": 180,
        "shell": False,
    },
    "brl-cad": {
        "kind": SUBPROCESS_CHECK,
        "cmd": ["bash", "-lc", "echo q | mged -c >/dev/null 2>&1"],
        "timeout": 60,
        "shell": False,
    },
    "calculix": {
        "kind": SUBPROCESS_CHECK,
        "cmd": ["/usr/bin/ccx", "-v"],
        "timeout": 30,
        "shell": False,
    },
    "eagle": {
        "kind": FILE_EXISTS_CHECK,
        "paths": ["/opt/eagle-7.7.0/bin/eagle"],
        "executable": True,
    },
    "fenics": {
        "kind": SUBPROCESS_CHECK,
        "cmd": [
            "bash",
            "-lc",
            "source activate fenicsx 2>/dev/null || conda activate fenicsx 2>/dev/null; "
            "python -c 'import dolfinx' >/dev/null 2>&1",
        ],
        "timeout": 60,
        "shell": False,
    },
    "floris": {
        "kind": SUBPROCESS_CHECK,
        "cmd": [
            "python3",
            "-c",
            "from floris import FlorisModel; "
            "fm = FlorisModel('defaults'); fm.run(); fm.get_turbine_powers()",
        ],
        "timeout": 90,
        "shell": False,
    },
    "freecad": {
        "kind": SUBPROCESS_CHECK,
        "cmd": ["bash", "-lc", "freecadcmd --version >/dev/null 2>&1"],
        "timeout": 30,
        "shell": False,
    },
    "freecad-path": {
        "kind": SUBPROCESS_CHECK,
        "cmd": ["bash", "-lc", "freecadcmd --version >/dev/null 2>&1"],
        "timeout": 30,
        "shell": False,
    },
    "fusion360": {
        "kind": FILE_EXISTS_CHECK,
        "paths": [
            r"C:\Users\Administrator\AppData\Local\Autodesk\webdeploy\production"
            r"\6a0c9611291d45bb9226980209917c3d\FusionLauncher.exe",
        ],
    },
    "kicad": {
        "kind": SUBPROCESS_CHECK,
        "cmd": ["bash", "-lc", "kicad-cli --version >/dev/null 2>&1"],
        "timeout": 30,
        "shell": False,
    },
    "openfoam": {
        "kind": SUBPROCESS_CHECK,
        "cmd": [
            "bash",
            "-lc",
            "source /opt/openfoam9/etc/bashrc && simpleFoam -help >/dev/null 2>&1",
        ],
        "timeout": 60,
        "shell": False,
    },
    "openscad": {
        "kind": SUBPROCESS_CHECK,
        "cmd": ["bash", "-lc", "openscad --version >/dev/null 2>&1"],
        "timeout": 30,
        "shell": False,
    },
    "openstudio": {
        "kind": SUBPROCESS_CHECK,
        "cmd": ["bash", "-lc", "openstudio --version >/dev/null 2>&1"],
        "timeout": 30,
        "shell": False,
    },
    "ptc-creo": {
        "kind": FILE_EXISTS_CHECK,
        "paths": [
            r"C:\Creo 12.4.0.0\Parametric\bin\parametric.exe",
            r"C:\Program Files\PTC\Creo 12.0.0.0\Parametric\bin\parametric.exe",
        ],
        "any": True,
    },
    "revit": {
        "kind": FILE_EXISTS_CHECK,
        "paths": [
            r"C:\Program Files\Autodesk\Revit 2027\Revit.exe",
            r"C:\Users\Administrator\Desktop\Revit 2027\Revit.exe",
        ],
        "any": True,
    },
    "sketchup": {
        "kind": FILE_EXISTS_CHECK,
        "paths": [
            r"C:\Program Files\SketchUp\SketchUp 2026\SketchUp\SketchUp.exe",
        ],
    },
}


# ---------------------------------------------------------------------------
# check_and_eval.py template.
#
# We keep the wrapper deliberately tiny and self-contained:
# - no third-party imports
# - same file works on Windows and Linux
# - subprocess stdout/stderr forwarded as bytes so eval.py's exact CRLF/LF
#   line endings are preserved verbatim for `exact_match`
# ---------------------------------------------------------------------------

WRAPPER_TEMPLATE = '''"""Auto-generated by task-gt/add_software_check.py. Do not edit by hand.

Smoke-tests that {app} is usable on this VM, then delegates to eval.py.
If the smoke test fails, prints `False` and exits 0 so the evaluator's
exact_match against `True\\r\\n` / `true\\r\\n` registers a clear failure.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

APP = {app!r}
HERE = Path(__file__).resolve().parent
EVAL_PY = HERE / "eval.py"


def check_software() -> bool:
{check_body}


def main() -> int:
    try:
        ok = check_software()
    except Exception:
        ok = False

    if not ok:
        sys.stdout.write("False\\n")
        sys.stdout.flush()
        return 0

    if not EVAL_PY.exists():
        sys.stdout.write("False\\n")
        sys.stdout.flush()
        return 0

    proc = subprocess.run(
        [sys.executable, str(EVAL_PY)],
        capture_output=True,
    )
    sys.stdout.buffer.write(proc.stdout)
    sys.stdout.buffer.flush()
    if proc.stderr:
        sys.stderr.buffer.write(proc.stderr)
        sys.stderr.buffer.flush()
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
'''


def _render_check_body(spec: dict[str, Any]) -> str:
    kind = spec["kind"]
    if kind == FILE_EXISTS_CHECK:
        paths = spec["paths"]
        any_match = bool(spec.get("any", False))
        executable = bool(spec.get("executable", False))
        path_lits = ",\n        ".join(repr(p) for p in paths)
        body = [
            "    candidates = [",
            f"        {path_lits},",
            "    ]",
        ]
        if executable:
            check = "os.path.exists(p) and os.access(p, os.X_OK)"
        else:
            check = "os.path.exists(p)"
        if any_match or len(paths) > 1:
            body.append(f"    return any({check} for p in candidates)")
        else:
            body.append(f"    return all({check} for p in candidates)")
        return "\n".join(body)

    if kind == SUBPROCESS_CHECK:
        cmd = spec["cmd"]
        timeout = int(spec.get("timeout", 60))
        cmd_lits = ",\n        ".join(repr(c) for c in cmd)
        body = [
            "    cmd = [",
            f"        {cmd_lits},",
            "    ]",
            "    try:",
            "        result = subprocess.run(",
            "            cmd,",
            "            capture_output=True,",
            f"            timeout={timeout},",
            "        )",
            "    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):",
            "        return False",
            "    return result.returncode == 0",
        ]
        return "\n".join(body)

    raise ValueError(f"unknown check kind: {kind!r}")


def render_wrapper(app: str) -> str:
    spec = CHECK_SPECS[app]
    body = _render_check_body(spec)
    return WRAPPER_TEMPLATE.format(app=app, check_body=body)


# ---------------------------------------------------------------------------
# JSON patching
# ---------------------------------------------------------------------------

EVAL_PY_RE = re.compile(r"(?<![A-Za-z0-9_])eval\.py\b")


def _find_eval_upload(postconfig: list) -> tuple[dict | None, dict | None]:
    """Return (step, file_entry) of the upload that ships eval.py to the VM."""
    for step in postconfig:
        if not isinstance(step, dict):
            continue
        if step.get("type") != "upload_file":
            continue
        params = step.get("parameters") or {}
        files = params.get("files") or []
        for f in files:
            if not isinstance(f, dict):
                continue
            local = (f.get("local_path") or "").replace("\\", "/")
            path = (f.get("path") or "").replace("\\", "/")
            if local.endswith("/eval.py") and path.endswith("/eval.py"):
                return step, f
            if local == "eval.py" and path.endswith("/eval.py"):
                return step, f
    return None, None


def _has_check_upload(postconfig: list, vm_path: str) -> bool:
    norm = vm_path.replace("\\", "/")
    for step in postconfig:
        if not isinstance(step, dict):
            continue
        if step.get("type") != "upload_file":
            continue
        params = step.get("parameters") or {}
        files = params.get("files") or []
        for f in files:
            if not isinstance(f, dict):
                continue
            if (f.get("path") or "").replace("\\", "/") == norm:
                return True
    return False


def _swap_eval_to_check(vm_path: str) -> str:
    head, sep, tail = vm_path.rpartition("eval.py")
    if not sep:
        return vm_path
    return head + "check_and_eval.py" + tail


def patch_task(task_dir: Path, app: str, dry_run: bool) -> str:
    json_path = task_dir / f"{task_dir.name}.json"
    if not json_path.exists():
        return f"skip (no json): {task_dir}"

    raw = json_path.read_text(encoding="utf-8")
    data = json.loads(raw)

    evaluator = data.get("evaluator")
    if not isinstance(evaluator, dict):
        return f"skip (no evaluator): {json_path}"

    postconfig = evaluator.get("postconfig")
    if not isinstance(postconfig, list):
        return f"skip (no postconfig list): {json_path}"

    eval_step, eval_entry = _find_eval_upload(postconfig)
    if eval_step is None or eval_entry is None:
        return f"skip (no eval.py upload): {json_path}"

    eval_vm_path = eval_entry["path"]
    eval_local_path = eval_entry["local_path"]
    use_backslash = "\\" in eval_vm_path

    if use_backslash:
        check_vm_path = eval_vm_path.rsplit("\\", 1)[0] + "\\check_and_eval.py"
    else:
        check_vm_path = eval_vm_path.rsplit("/", 1)[0] + "/check_and_eval.py"

    local_sep = "\\" if "\\" in eval_local_path else "/"
    check_local_path = eval_local_path.rsplit(local_sep, 1)[0] + local_sep + "check_and_eval.py"
    if local_sep == "/" and "/" not in eval_local_path:
        # eval_local_path was just "eval.py"
        check_local_path = "check_and_eval.py"

    changed = False

    if not _has_check_upload(postconfig, check_vm_path):
        postconfig.append({
            "type": "upload_file",
            "parameters": {
                "files": [
                    {
                        "local_path": check_local_path,
                        "path": check_vm_path,
                    }
                ],
            },
        })
        changed = True

    result = evaluator.get("result")
    if isinstance(result, dict):
        cmd = result.get("command")
        if isinstance(cmd, str) and "eval.py" in cmd and "check_and_eval.py" not in cmd:
            new_cmd = EVAL_PY_RE.sub("check_and_eval.py", cmd)
            if new_cmd != cmd:
                result["command"] = new_cmd
                changed = True

    new_text = json.dumps(data, ensure_ascii=False, indent=2)
    if raw.endswith("\n") and not new_text.endswith("\n"):
        new_text += "\n"

    wrapper_path = task_dir / "check_and_eval.py"
    wrapper_body = render_wrapper(app)
    wrapper_changed = (
        not wrapper_path.exists()
        or wrapper_path.read_text(encoding="utf-8") != wrapper_body
    )

    if not changed and not wrapper_changed:
        return f"ok (already up to date): {json_path}"

    if dry_run:
        bits = []
        if changed:
            bits.append("would patch json")
        if wrapper_changed:
            bits.append("would write check_and_eval.py")
        return f"{', '.join(bits)}: {json_path}"

    if changed and new_text != raw:
        json_path.write_text(new_text, encoding="utf-8", newline="\n")
    if wrapper_changed:
        wrapper_path.write_text(wrapper_body, encoding="utf-8", newline="\n")

    return f"patched: {json_path}"


def iter_task_dirs(app_filter: str | None, task_filter: str | None):
    if not ROOT.exists():
        return
    for app_dir in sorted(ROOT.iterdir()):
        if not app_dir.is_dir():
            continue
        app = app_dir.name
        if app not in CHECK_SPECS:
            print(
                f"WARN: no check spec for app {app!r}, skipping",
                file=sys.stderr,
            )
            continue
        if app_filter and app_filter != app:
            continue
        for task_dir in sorted(app_dir.iterdir()):
            if not task_dir.is_dir():
                continue
            if task_filter and task_filter != task_dir.name:
                continue
            yield app, task_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="do not write files, just print what would change")
    parser.add_argument("--app", help="only process this app dir, e.g. autocad")
    parser.add_argument("--task", help="only process this task dir, e.g. task-04")
    args = parser.parse_args()

    if not ROOT.exists():
        print(f"ERROR: {ROOT} does not exist", file=sys.stderr)
        return 2

    total = 0
    patched = 0
    skipped = 0
    for app, task_dir in iter_task_dirs(args.app, args.task):
        total += 1
        try:
            status = patch_task(task_dir, app, args.dry_run)
        except json.JSONDecodeError as e:
            print(f"ERROR: failed to parse {task_dir}: {e}", file=sys.stderr)
            continue
        if status.startswith("ok") or status.startswith("skip"):
            skipped += 1
        else:
            patched += 1
        print(status)

    mode = "dry-run" if args.dry_run else "write"
    print(f"\n[{mode}] total={total} patched={patched} skipped={skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
