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
