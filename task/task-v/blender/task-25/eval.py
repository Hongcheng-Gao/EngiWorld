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
