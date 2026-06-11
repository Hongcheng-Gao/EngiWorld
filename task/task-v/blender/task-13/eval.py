from __future__ import annotations

import base64
import importlib.util
import json
import subprocess
import shutil
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')

GUI_BYPASS_FORBIDDEN_EXTENSIONS = {
    ".py", ".pyw", ".ipynb", ".sh", ".bash", ".zsh", ".bat", ".cmd",
    ".ps1", ".psm1", ".psd1", ".vbs", ".js", ".mjs", ".ts", ".rb",
    ".lua", ".tcl", ".ahk", ".scr",
}
GUI_BYPASS_ALLOWED_FILENAMES = {"eval.py"}
GUI_BYPASS_OUTPUT_TOKENS = (
    "result.ifc", "result.pdf", "result.osm", "workflow.osw", "summary.txt",
    "report.csv", "result.csv",
    ".dxf", ".dwg", ".step", ".stp", ".fcstd", ".scad", ".stl", ".obj",
    ".blend", ".pcb", ".sch", ".brd", ".dsn", ".opj",
    ".db", ".rst", ".rth", ".wbpj", ".odb", ".cae", ".inp",
    ".nc", ".gcode", ".slb", ".ipt", ".sldprt", ".sldasm",
    "autocad_result", "apdl_", "wb_",
)
GUI_BYPASS_COMMAND_TOKENS = (
    "python", "python3", "py ", "powershell", "pwsh", "cmd.exe", "cmd /c",
    "bash", " sh ", "zsh", "node", "ruby", "perl",
    "ifcopenshell", "openstudio", "energyplus",
    "blender --background", "revitbatchprocessor",
    "ansys", "mapdl", "fluent", "abaqus", "cae noGUI",
    "freecad", "freecadcmd", "openscad", "librecad",
    "ezdxf", "cadquery", "accoreconsole", "autolisp",
    "solidworks", "solvespace", "kicad-cli", "pcbnew",
)


def _read_text_safe(path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _desktop_script_artifacts(root):
    if not root.exists() or not root.is_dir():
        return True
    try:
        candidates = list(root.iterdir())
        for directory in list(candidates):
            if directory.is_dir() and directory.name not in {"__pycache__", "_runtime"}:
                try:
                    candidates.extend(directory.iterdir())
                except Exception:
                    pass
        for path in candidates:
            if not path.is_file():
                continue
            if path.name in GUI_BYPASS_ALLOWED_FILENAMES:
                continue
            if path.suffix.lower() in GUI_BYPASS_FORBIDDEN_EXTENSIONS:
                return True
    except Exception:
        return True
    return False


def _history_paths(root):
    home = Path.home()
    return [
        home / ".bash_history",
        home / ".zsh_history",
        home / ".python_history",
        home / ".local/share/fish/fish_history",
        home / "AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt",
        home / "AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/Visual Studio Code Host_history.txt",
        root / ".bash_history",
        root / ".zsh_history",
    ]


def _history_contains_bypass(root):
    for path in _history_paths(root):
        if not path.is_file():
            continue
        text = _read_text_safe(path).lower()
        if not text:
            continue
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or "eval.py" in line:
                continue
            touches_output = any(token in line for token in GUI_BYPASS_OUTPUT_TOKENS)
            runs_command = any(token in line for token in GUI_BYPASS_COMMAND_TOKENS)
            writes_file = any(
                token in line for token in (">", "tee ", "cat ", "set-content", "out-file", "new-item")
            )
            if touches_output and (runs_command or writes_file):
                return True
            if ("/desktop/" in line or "\\desktop\\" in line) and any(
                ext in line for ext in GUI_BYPASS_FORBIDDEN_EXTENSIONS
            ) and runs_command:
                return True
    return False


def check_no_gui_bypass(root):
    root = Path(root)
    if _desktop_script_artifacts(root):
        return False
    if _history_contains_bypass(root):
        return False
    return True

BLENDER_PATH = "blender"

BUNDLE = {'eval_inner.py': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['/home/user/Desktop/answer.blend']
INIT_MAP = [('env.exr', '/home/user/Desktop/env.exr'), ('scene.blend', '/home/user/Desktop/scene.blend')]


def _decode(payload: str) -> bytes:
    return zlib.decompress(base64.b64decode(payload.encode("ascii")))


def _materialize_bundle(root: Path) -> None:
    for rel, payload in BUNDLE.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_decode(payload))
    for dirname in ("init_file", "ground_truth", "_internal"):
        (root / dirname).mkdir(parents=True, exist_ok=True)
    for rel, desktop_path in INIT_MAP:
        src = Path(desktop_path)
        dst = root / "init_file" / rel
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def _bundle_python_paths(root: Path) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        text = str(path)
        if text not in seen:
            seen.add(text)
            paths.append(text)

    add(root)
    for rel in BUNDLE:
        rel_path = Path(rel)
        if rel_path.suffix == ".py" and rel_path.parent != Path("."):
            add(root / rel_path.parent)
    return paths


def _load_module(root: Path):
    spec = importlib.util.spec_from_file_location("eval_inner", root / "eval_inner.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load eval_inner.py")
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules["eval_inner"] = module
    added_paths = _bundle_python_paths(root)
    for path in reversed(added_paths):
        sys.path.insert(0, path)
    try:
        spec.loader.exec_module(module)
    finally:
        for path in added_paths:
            try:
                sys.path.remove(path)
            except ValueError:
                pass
    return module


def _is_pass(result) -> bool:
    if isinstance(result, bool):
        return result
    if isinstance(result, dict):
        if "pass" in result:
            return bool(result["pass"])
        if "passed" in result:
            return bool(result["passed"])
        score = result.get("score")
        if isinstance(score, (int, float)):
            return float(score) == 1.0
    for attr in ("all_passed", "passed"):
        if hasattr(result, attr):
            value = getattr(result, attr)
            if isinstance(value, bool):
                return value
    if hasattr(result, "score"):
        try:
            return float(getattr(result, "score")) == 1.0
        except Exception:
            pass
    return False


def _resolve_arg(spec: str):
    if spec == "__DESKTOP_DIR__":
        return str(DESKTOP)
    return spec


def _call_inner(root: Path):
    module = _load_module(root)
    func = getattr(module, CALL_FUNC)
    args = [_resolve_arg(arg) for arg in CALL_ARGS]
    return func(*args)


def _have_bpy() -> bool:
    try:
        import bpy  # noqa: F401
        return True
    except Exception:
        return False


def _run_via_blender(root: Path) -> bool:
    result_path = root / "_blender_result.json"
    runner_path = root / "_blender_runner.py"
    added_paths = _bundle_python_paths(root)
    args = [_resolve_arg(arg) for arg in CALL_ARGS]
    runner_code = f"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path({str(root)!r})
RESULT_PATH = Path({str(result_path)!r})
CALL_FUNC = {CALL_FUNC!r}
CALL_ARGS = {args!r}
ADDED_PATHS = {added_paths!r}


def _is_pass(result):
    if isinstance(result, bool):
        return result
    if isinstance(result, dict):
        if "pass" in result:
            return bool(result["pass"])
        if "passed" in result:
            return bool(result["passed"])
        score = result.get("score")
        if isinstance(score, (int, float)):
            return float(score) == 1.0
    for attr in ("all_passed", "passed"):
        if hasattr(result, attr):
            value = getattr(result, attr)
            if isinstance(value, bool):
                return value
    if hasattr(result, "score"):
        try:
            return float(getattr(result, "score")) == 1.0
        except Exception:
            pass
    return False


spec = importlib.util.spec_from_file_location("eval_inner", ROOT / "eval_inner.py")
if spec is None or spec.loader is None:
    raise RuntimeError("unable to load eval_inner.py")
module = importlib.util.module_from_spec(spec)
sys.modules["eval_inner"] = module
for path in reversed(ADDED_PATHS):
    sys.path.insert(0, path)
try:
    spec.loader.exec_module(module)
    func = getattr(module, CALL_FUNC)
    value = func(*CALL_ARGS)
    RESULT_PATH.write_text(json.dumps({{"pass": _is_pass(value)}}), encoding="utf-8")
finally:
    for path in ADDED_PATHS:
        try:
            sys.path.remove(path)
        except ValueError:
            pass
"""
    runner_path.write_text(runner_code, encoding="utf-8")
    try:
        proc = subprocess.run(
            [BLENDER_PATH, "--background", "--factory-startup", "--python", str(runner_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
    except Exception:
        return False
    if result_path.exists():
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            return bool(payload.get("pass"))
        except Exception:
            return False
    return proc.returncode == 0




def _run() -> bool:
    if not check_no_gui_bypass(DESKTOP):
        return False

    import uuid

    runtime_base = Path(__file__).resolve().parent / "_runtime"
    runtime_base.mkdir(parents=True, exist_ok=True)
    root = runtime_base / ("engiworld_eval_" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    try:
        _materialize_bundle(root)
        if _have_bpy():
            return _is_pass(_call_inner(root))
        return _run_via_blender(root)
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    print("True" if _run() else "False")
