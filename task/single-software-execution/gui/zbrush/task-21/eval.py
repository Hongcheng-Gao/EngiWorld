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
