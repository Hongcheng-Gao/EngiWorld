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

BUNDLE = {'eval_inner.py': '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', 'ground_truth/fulladd_placed.brd': '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H9J5X6gmL+W7CWsdnreCxned97lq8lK+m7E+4nlvRZ5nq8lL+W7B/H97pDXy3crzIu61zh/npXy3+eS9ugZ5Kd/tPnmvrEFeyrfaJ2+/GuSlfHf45D2gBnkp350+efvUIC/lu8sn7341yEv51vjkTa9BXsp3t0/e3jXIS/nWsucgMcj7APLGVtMmKd89WHPyvPchT51q8lK+e33K/HMN2jPlu88n7081yEv57vfJ+0MN8t6vvPfcdt7v/yAvfaaFPnvzINblkdIhdA8O3Yv1P7+PecQ1+nPPtuh9MGnjv/kZminzxI6eVmdDc7uhbf+6zbEtPBX592RHXdP/ct1r0uZrYjOzpae7SnnaYLyrg2eQ/8aYl/A3Xv/aMubtllKrBterJjb/5bpX1+a3x+avjjE7W3k6qPh6V+nO+jg9O1iIObF0GZHtkOyRfy5f0OdYom8b7eN+842j1lnHK6OISZMrIyIiIiIiIiIiIiLyd4ljUURERPq9iIjIrtXXRURERERERERERERERERERERERP4b4vwBRURERERERHaPuYCIiIiIiIjIrr3eFxERERERERERERGReb6IiIj0exERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERGR3U0CyhHdjbWB6G6p0valr4ru3NoKKv1VVMYK0epVhVTavvR7Uen3otL3RWUtLyr9X3TX0To+Km1fVMYAmQOISh8WlT4sKmOCqIwJotKvRaVfi8pYISpjhaj0d1Hp76LS10Wlr4tKvxeVz+uJylggKnMAUen3otLvRaWPi8o8X1T6vaj0e1Hp96IypxeVsUBUxgJR6fei0u9Fpe+Lhn+rT/q+qGj12moXVLmuonIPrNlv2e6qfb+VqKioqKio6C6gKorKuREVFRUVFd3VVURERERERERERERE/g62qLy/F5XP6opKXxWVv4MtKmOFqHz/XlT6vaj0e1Hp+6KylheV/i8qfwdbVMYAUZkDiEofFpU+LCpjgqiMCaLSr6Vfi4rKWCEqY4Wo9HdR6e/S10Wlr4tKvxeVz+uJylggKnMAUen3otLvRaWPi8o8X1T6vaj0e1Hp96IypxeVsUBUxgJR6fei0u9Fpe+Lyt/BFhWVv4MtfwdbVO738new5e9gi4qKioqKisrfwRYVFRUVFRWVv4MtIiIi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'}
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
