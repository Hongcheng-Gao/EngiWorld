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
