from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\user\Desktop')

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
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('scene.obj', 'C:\\Users\\user\\Desktop\\scene.obj')]


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


def _materialize_desktop_view(root: Path) -> Path:
    stage = root / "_desktop_view"
    stage.mkdir(parents=True, exist_ok=True)
    if DESKTOP.exists():
        for item in DESKTOP.iterdir():
            if item.name in {"eval.py", "_runtime"}:
                continue
            dst = stage / item.name
            if item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)
            elif item.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dst)
    for rel, desktop_path in INIT_MAP:
        src = Path(desktop_path)
        if src.exists():
            dst = stage / "initial_files" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    return stage


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


def _resolve_arg(spec: str, desktop_view: Path):
    if spec == "__DESKTOP_DIR__":
        return str(desktop_view)
    desktop_prefix = str(DESKTOP)
    if spec.startswith(desktop_prefix):
        rel = spec[len(desktop_prefix):].lstrip("\\/")
        return str(desktop_view / Path(rel)) if rel else str(desktop_view)
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
        desktop_view = _materialize_desktop_view(root)
        module = _load_module(root)
        func = getattr(module, CALL_FUNC)
        args = [_resolve_arg(arg, desktop_view) for arg in CALL_ARGS]
        result = func(*args)
        return _is_pass(result)
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("True" if _run() else "False")
