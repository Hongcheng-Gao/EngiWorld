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
INIT_MAP = [('spec_list.json', 'C:\\Users\\user\\Desktop\\spec_list.json'), ('template.OutJob', 'C:\\Users\\user\\Desktop\\template.OutJob')]


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
