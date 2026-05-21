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
INIT_MAP = [('2layer.cam', '/home/user/Desktop/2layer.cam'), ('blinker.brd', '/home/user/Desktop/blinker.brd')]


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
