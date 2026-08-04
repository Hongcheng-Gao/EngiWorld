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
