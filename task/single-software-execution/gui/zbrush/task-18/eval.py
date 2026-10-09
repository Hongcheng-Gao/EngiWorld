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
CALL_ARGS = ['C:\\Users\\user\\Desktop\\output.obj']
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
