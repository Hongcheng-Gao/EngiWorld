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
 'init_file/2layer.cam': 'eNrtVs1q20AQvgfyDoOh0BbiWo6dpMUOpI4TKPkxdqAtaQgraSRvvdKK3VXc5sF6yi0v1llLVqzE8aHU4IMYhL3z881qZj7tXveOzmGgpIdaSwVfpHuzvXWM2lM8MVzG1z7edGsd97Cv7jENDfR/GYx99HdOUbmodk6kipiBt8NRc7/17V3ng3vYSQ5/xMccNSog+B0CBRe1wbEBlmoIHh/iAI4onButvbHihjAhjX3APMsJKsPDNA61z6yNQhQgjxHup8gFC3mIMBDMkKpO+eYpc+xsbzaUUzDGZsyEhTkuwD51XEUhn2lbjw/exGbStB0EeF/3oiSznj3+MYVWS/EyxlepNwHpEiq5JMJbCDQyEYysS3Nos8y1nNBo61Ir9wPjrB+nGKOi19FFR/K3hqwjRSOuxlzbNsBPaoMnY80JGGQAAb9D0OhZWA1UIgNhDgpUOgYBDQQDM5Ug2G8CdiVTflHt7zKFKReCgkyGFWb5Ay4wx6N0hvG4gMur7skokTG1BTT3cbHiVGSfIGbqxZprLiZUA6Q6PwteLPs8msq5xK0o+aLbU8JyyUdZXbr0e+uUl83ycre8bJWX7e2t7a3rGQoR64JFmDHqxVDUcuusv73S5slEDI0Sk4XOBuKOe9itnfaHn/vD24x7pP86RhTdWn06FrQa0kjN3EceE9il17hMTZKabu3NhS05WU6ISrpba4AVZ/Y4pO5HKXELcwMpLoNAIwU26o2IC8h+LDIlNBb5SgqanNibx8A8coDxU5hds5B8nGajkSsP5v/IeGbnjPZjt7EPzgGpelLIXNVc+eyRtODgVWmROLnskmQx1tLOPZz/Li3K0aJcdm9OJf8sdnByGjVLNCo+mCX6jJ6+ImvhDn00Npk7exV5KllKnt1Xz6DZRaZMIjpyIT9ze+eDtRCJTu4NJlKzAU0a9HZFpEqeEan18hSi22TE9ARh9dVutHD5tP5r4xZddzeZWx8rVlXyjFXtFaxafdMr2DS6PFsTm/QGs2m3UbGpkjmb/gL7Pps6',
 'init_file/blinker.brd': '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'}
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
