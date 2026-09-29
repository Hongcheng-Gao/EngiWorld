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
