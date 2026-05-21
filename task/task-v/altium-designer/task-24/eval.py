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

BUNDLE = {'eval_inner.py': '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', 'ground_truth/custom.PCBDwf': 'eNpVUcFuwyAMvUfiH/IDq9J2Vw5pNmmToqwqUS/VDjS4KyrYEVBF3dcPQqtqB2T8sN97NocPkArcNyvypb+NwN+cPAVvJbJiD85rQr5eVKxgxUGcAUKsnqPQv8DrdXtPv5wGDDKk+lai8oMc4f7Wgx2NDJEbTvJqQt2Jz5mw18HAxtBwiawN2VHijXcwNeTG8t3AEByhHnzZBrVgRa2UA+/5crUuBVmYzuCgFIEV2zMh8KqqXuLJZvcaJr+DUyzBAXwUSEhDVwx8lZMl72msvQd7NLcMrfiGQiD7RCPVhqRTO5BGezuPT1MyGyUxRDcZEdpcxOAAMCGx681pY3p5NBB75thJm/b7gGNZq/ECKgn/tyLIxY3GL+G1HwCVxp+ssk17VA/NjvAJNGSuFvOAr6z4A6HKnqM='}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('mods.json', 'C:\\Users\\user\\Desktop\\mods.json'), ('orig.PCBDwf', 'C:\\Users\\user\\Desktop\\orig.PCBDwf')]


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
