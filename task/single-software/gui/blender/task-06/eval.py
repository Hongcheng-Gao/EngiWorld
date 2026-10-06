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
