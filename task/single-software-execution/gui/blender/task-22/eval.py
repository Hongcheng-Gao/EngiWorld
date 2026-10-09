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
