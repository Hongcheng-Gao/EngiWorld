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
