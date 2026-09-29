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
