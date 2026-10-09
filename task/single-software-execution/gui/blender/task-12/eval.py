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
