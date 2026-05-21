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
