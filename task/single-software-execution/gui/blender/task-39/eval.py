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
