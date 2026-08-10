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

BUNDLE = {'eval_inner.py': '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',
 'common/schema.py': 'eJyNVF2O0zAQfq/UOwzhJRWQXfEYqWgrVCQkBKvuvpUqMsmYhnXtyHYRVYnEIbjIXoGjcBLGP2lSWpZNIiWefPPNj79xkiTj0fwrEws0W2HBlGvcMPj94yfYNYKxTFZMV6DRbrUEu2sQuNLAhAAkty2zmDU78tN1Y002HiWOkWu1gYpZVgpmDBqoN43Stjc9B16jqCKSaGv5uQPN5G48cvfVAT4e+Re8XmN5F1LNxyOgS7IN5pSnDsvGhaty+KSUCBb81mBpnY14YQrvlcTwh5V2y8Sp3SqBmsmSeLlQzMJ3//MII5UNYcnqCg7WCjkUBVmLIjUo+CQm6S5qpd0aB7+e3dwkUHNwkCxkDCgMQvJm9vZd0vs0TFvnsuTJch8I2hXsvZ8rvE1WPbgj7AqG2rg0fdKDPA68GWsalFXKk85juj8iaJPJKXto2uO5Az4yh8UTfZb50PbHk5PL9Nf9/tj9LLnfrwe50v0B2E6GFFH6CdDzzL+yL6qWqfef/Eup/UzFsJaZu6KuBlo1FpuC12Ko39IJ3OQgamOXA7WvSAV+YlLSGCNDwamZSu+mDhmzRa2VDqo8kizAU+qCdc24uZ1fA2cUtCKdA8m76sR71WjVoLa7XstBm0HK8OIV1NLmJ40x201adjJ2Z0NJuND1UM3kgQhWWSb+E0CgTB9JZ0qlsafz45ufGRHXKKAnKodygOkULv9SSIx/mV2eFj0Y3YsBzfAkoMZsmN716dDGDCKIWmIc7lvSRhzrKJM2j+sQo73Y9zHaqJK4PQCpLzvOmP/Os5ecVHzudPAaOa7TZ9JPAsB8sfiw6DLwHkdDdW6TH6KkutNycmakPso4Sx5OgD8nCfRs',
 'init_file/topside.brd': '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'}
CALL_FUNC = 'evaluate'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('topside.brd', '/home/user/Desktop/topside.brd')]


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
