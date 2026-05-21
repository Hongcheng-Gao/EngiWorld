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
