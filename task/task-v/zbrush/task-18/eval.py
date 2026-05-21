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
