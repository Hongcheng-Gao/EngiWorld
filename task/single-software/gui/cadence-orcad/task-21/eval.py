from __future__ import annotations

import base64
import contextlib
import importlib.util
import io
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

BUNDLE = {'eval_inner.py': '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', 'ground_truth/fulladd_placed.brd': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('fulladd.brd', r'C:\Users\user\Desktop\fulladd.brd')]


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
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = func(*args)
        return _is_pass(result)
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("True" if _run() else "False")
