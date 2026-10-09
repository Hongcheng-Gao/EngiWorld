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
