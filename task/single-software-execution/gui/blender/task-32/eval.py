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
CALL_ARGS = ['/home/user/Desktop/scene.obj']
INIT_MAP = [('scene.blend', '/home/user/Desktop/scene.blend'), ('stub.obj', '/home/user/Desktop/stub.obj')]


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
