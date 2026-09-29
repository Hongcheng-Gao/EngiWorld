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
