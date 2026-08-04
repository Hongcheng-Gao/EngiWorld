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
INIT_MAP = [('broken_amp.sch', '/home/user/Desktop/broken_amp.sch')]


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
