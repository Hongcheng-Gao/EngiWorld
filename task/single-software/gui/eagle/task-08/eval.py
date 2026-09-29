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

BUNDLE = {'eval_inner.py': 'eNqdVm1v2zYQ/q5fwXFfqNZR7KT5MGNOkDVeYCxNi8RdBySFQJtnm4goaSSdxmj733dHSbaUpm8L4JgW7+V5js8dxTkf38tsLX1h2QI/Xrq7vcMjJs7fTtgM8vnKSHs3ZF4vVx5ypsDpZc7sOgPHdL43K6RVccI5jxa2MCxNF2u/tpCmTJuysJ7JPC+89LrIXRTVzyw0K7dxzfLBZAl4C5CMMzCQ+ymumXRsPK1il9KvMj1rAr/Bn1GEARLaSHTuwHrR7zHnraBNgWB0hlDixIIrsnsQMdpaDF1/sX3G54UxRc7juEri5iswssnxcgXzuytw68z3GFWqWjP2K8uLf+WQjV/0D6Joenr9Vzo5YyPGQS4zwAry6GJ8mV6N8ZmFBJOUCEVYLvZObtVzcTK8TfA7Polv3TNhzCejs5j3yHZyfvn6avzy9HocR1GkYMFSX6TGCDckajHbO2aLrJCefWKXRQ7DiOGfwURVxsSBtPOVcHHY0AuE6pmpzOjPAp5QHnzDM6SFziGkMMnSFutSDOLKu7YlEwzU7B7ESVZ8ACtiNkLOxnAGmYNg9oz1k/7B0YsGO1ZaGmGLwmO1ps3Z9lguDXyLEKmxRIkxck0WOlcyywRP9vcrDQYJ7ofoPN6RQ5RlsgQvOCXgAWBItbVo0aoLWztQIwCeAedd8qFQFRuomgWEW8+Mdg5VnSptdzx2GqkSoh3WNqix69LSZJULzXbOgvow1WpUK4tEDWWQ84jkjbEQY3D00iJ69N6eJ1WOKFPxbnjo3GRmFTGTucNjC7/e7yoyl7nSCmlhFAK8H9zbJd1aJPCgnXci7tZzC2Jr2NmeWZB3jRprW+1ahx0qkIC1BdVhwRVk+h6snGUQ1Lso1rkiPh8R32cm4KGEuQfFtuxi/ljftq6P3bRyoJao0FMaAA5EhSWm86et+izgYQ6lZ+PwhedFQ6gDdE5jwSWyLCFXojUkRIc2VXFEstIqxenGe53dUjoHavSnxM7p7jTsRjygDFUYn55fjFkYt+yfVxePYsm5X8ssSAPi3Vat4y+L8kMUvg6/hj616xbyn0NdI+bFXf2w0bMiBWx7/nHD8/hn8a+kS9sBvmCBCVGLpDLS41N8fm/5H7MSGxcn2NNcSODdgNVk5KH18+WObN0NlfGjTuicFbXzHWx6LFBOiVWP+RWiWBVZaIqbrafgRr3TFuhD/W5U+gGX1b8lpP1ycITTuoczenDUEkrj90aqtlsp1Y94/a1l2+tey+95nVmdZbWPonXlcNivHQ77XQf3Tiu/Cg4Ok+D6OxncLoP7dobWHDR0ibYurB7VPf6ffd86rafaHu/8jkpwblL+52wAe7+x49HuhOOvDIcFR6uPW7NhcrD4TOSeGgzGdIZC1FVZhDpMA1R8baMLPU2N1Hma8mEj0wxyQa9aOC/vY/bLiB3sylZaneP1uXZyiTd6ufErHJl0Uyblhl2//ePV5Pp68voyPZtcYemrOwxDOa9w4O/KS8/wdvH4dlHjC69ao9alWwO4GbyvTKrMlWHi1gbfVTei7q1tuD7hb2zmhQWiOEj6VWMO4ug/3QM8hw==', 'common/schema.py': 'eJyNVF2O0zAQfq/UOwzhJRWQXfEYqWgrVCQkBKvuvpUqMsmYhnXtyHYRVYnEIbjIXoGjcBLGP2lSWpZNIiWefPPNj79xkiTj0fwrEws0W2HBlGvcMPj94yfYNYKxTFZMV6DRbrUEu2sQuNLAhAAkty2zmDU78tN1Y002HiWOkWu1gYpZVgpmDBqoN43Stjc9B16jqCKSaGv5uQPN5G48cvfVAT4e+Re8XmN5F1LNxyOgS7IN5pSnDsvGhaty+KSUCBb81mBpnY14YQrvlcTwh5V2y8Sp3SqBmsmSeLlQzMJ3//MII5UNYcnqCg7WCjkUBVmLIjUo+CQm6S5qpd0aB7+e3dwkUHNwkCxkDCgMQvJm9vZd0vs0TFvnsuTJch8I2hXsvZ8rvE1WPbgj7AqG2rg0fdKDPA68GWsalFXKk85juj8iaJPJKXto2uO5Az4yh8UTfZb50PbHk5PL9Nf9/tj9LLnfrwe50v0B2E6GFFH6CdDzzL+yL6qWqfef/Eup/UzFsJaZu6KuBlo1FpuC12Ko39IJ3OQgamOXA7WvSAV+YlLSGCNDwamZSu+mDhmzRa2VDqo8kizAU+qCdc24uZ1fA2cUtCKdA8m76sR71WjVoLa7XstBm0HK8OIV1NLmJ40x201adjJ2Z0NJuND1UM3kgQhWWSb+E0CgTB9JZ0qlsafz45ufGRHXKKAnKodygOkULv9SSIx/mV2eFj0Y3YsBzfAkoMZsmN716dDGDCKIWmIc7lvSRhzrKJM2j+sQo73Y9zHaqJK4PQCpLzvOmP/Os5ecVHzudPAaOa7TZ9JPAsB8sfiw6DLwHkdDdW6TH6KkutNycmakPso4Sx5OgD8nCfRs'}
CALL_FUNC = 'evaluate'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('README.txt', '/home/user/Desktop/README.txt'), ('loose.brd', '/home/user/Desktop/loose.brd')]


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
