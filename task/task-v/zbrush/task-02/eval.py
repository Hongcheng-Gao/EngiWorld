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
