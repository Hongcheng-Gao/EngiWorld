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
INIT_MAP = [('scene.blend', '/home/user/Desktop/scene.blend')]


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
