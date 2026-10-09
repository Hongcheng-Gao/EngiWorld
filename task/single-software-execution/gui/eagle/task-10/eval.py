from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')

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

BUNDLE = {'eval_inner.py': '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', 'common/schema.py': 'eJyNVF2O0zAQfq/UOwzhJRWQXfEYqWgrVCQkBKvuvpUqMsmYhnXtyHYRVYnEIbjIXoGjcBLGP2lSWpZNIiWefPPNj79xkiTj0fwrEws0W2HBlGvcMPj94yfYNYKxTFZMV6DRbrUEu2sQuNLAhAAkty2zmDU78tN1Y002HiWOkWu1gYpZVgpmDBqoN43Stjc9B16jqCKSaGv5uQPN5G48cvfVAT4e+Re8XmN5F1LNxyOgS7IN5pSnDsvGhaty+KSUCBb81mBpnY14YQrvlcTwh5V2y8Sp3SqBmsmSeLlQzMJ3//MII5UNYcnqCg7WCjkUBVmLIjUo+CQm6S5qpd0aB7+e3dwkUHNwkCxkDCgMQvJm9vZd0vs0TFvnsuTJch8I2hXsvZ8rvE1WPbgj7AqG2rg0fdKDPA68GWsalFXKk85juj8iaJPJKXto2uO5Az4yh8UTfZb50PbHk5PL9Nf9/tj9LLnfrwe50v0B2E6GFFH6CdDzzL+yL6qWqfef/Eup/UzFsJaZu6KuBlo1FpuC12Ko39IJ3OQgamOXA7WvSAV+YlLSGCNDwamZSu+mDhmzRa2VDqo8kizAU+qCdc24uZ1fA2cUtCKdA8m76sR71WjVoLa7XstBm0HK8OIV1NLmJ40x201adjJ2Z0NJuND1UM3kgQhWWSb+E0CgTB9JZ0qlsafz45ufGRHXKKAnKodygOkULv9SSIx/mV2eFj0Y3YsBzfAkoMZsmN716dDGDCKIWmIc7lvSRhzrKJM2j+sQo73Y9zHaqJK4PQCpLzvOmP/Os5ecVHzudPAaOa7TZ9JPAsB8sfiw6DLwHkdDdW6TH6KkutNycmakPso4Sx5OgD8nCfRs'}
CALL_FUNC = 'evaluate'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('bus.sch', '/home/user/Desktop/bus.sch')]


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
