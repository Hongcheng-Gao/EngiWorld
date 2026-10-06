from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
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

BUNDLE = {'eval_inner.py': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['/home/user/Desktop/part.fbx']
INIT_MAP = [('dummy.fbx', '/home/user/Desktop/dummy.fbx'), ('scene.blend', '/home/user/Desktop/scene.blend')]


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
        module = _load_module(root)
        func = getattr(module, CALL_FUNC)
        args = [_resolve_arg(arg) for arg in CALL_ARGS]
        result = func(*args)
        return _is_pass(result)
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("True" if _run() else "False")
