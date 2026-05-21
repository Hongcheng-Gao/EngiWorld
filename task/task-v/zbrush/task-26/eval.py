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
