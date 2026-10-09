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
CALL_ARGS = ['/home/user/Desktop/animated.abc']
INIT_MAP = [('scene.blend', '/home/user/Desktop/scene.blend'), ('stub.abc', '/home/user/Desktop/stub.abc')]


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
