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

BUNDLE = {'eval_inner.py': 'eNqVVE1P3DAQvedXuL40LmxoUQ/ViiCtChVHhDh1szUmngS3iWPZDlqx2v/esZPsBqEidQ/J2vPmzZuPTGW7lnBe9b63wDlRremsJ0LrzguvOu2SZLz77To9/beQVMHTCP/UqMfJ7RaPSXJzfXdN8nhIkVo1SMwyC65rniFlmREWtE+uVvfXPCItZGXXGgSmlq5Xi5+btVi8bHbne/LqVLiTQu6+nOJ9IQu5PDzwuPu6pyy5Xd3f/IMzcCzP1r8uLj8WtHCfNieITxIJFeG6s61o1AukHrZ+SZy3jCwuw3uZEPyFayQdJWeuf0zpRThd0tNoZHPYqCLCGtE+SkHa5VCPNqtt15v0M2OZFi3MvS1gE3S8wGqZRpSQ0sIWGmNQfLIM9SiTTrLhWTS8673pvUuHN5fKHuVLVfpB/2CdmnLEztoScUI7BI3oM0KlLTO/9TQa60AQm4uWkIaW3NveP9E3UJQf5iEnO2qEc3RJfojGYbb0GJtGoaMYto9+qiI4eEFGBlvlMC82JHAkXVMLAkeRbpC+orA1UHqQk+hWOad0vSS7QBJKvKczhljhgWgKOOt+cEF2TAt7kIIuO4lcOe19tfiGXQBrO+tyqmr0AcoY+ZDP/Q+Bav9fPNHv/Uzp1d33qaxSVRVYR+IneCjAqmkAuxIuEPRe0hN9bE0gv7c9vLKUT1D+GWxr+jCGXTwTbPLDodLCI8wRUXmwcROcSeGBTOWI64NukrcacKVg2XloDq6cHJPjvBVKc06HGkxbyNa4Kxwkw2waVDNdZStb9y2ukdtwstP4mkxIycVoS+fTNiJsHSYcgZEmQN3obKxCl7DlMtm3xqWvvq8AzGYfzilRWmKM/BzbqV3YnsKVSuVx0BlL/gKXGLqp', 'ground_truth/drc.txt': 'eNq1j09vozAQxe9IfIdRTl3J5Y9D2jQ3ltCq2gQi8O4eIwemLarBrLG1zbevW6oKVT1FymU082b03m/WRQKpUlJBgb1U2nXWK1/Iiov/Uj37affY2EbUvqfbfi9Vxet9r+QBI7/GVnoHVbvOVnYQ9wroNYQ3q+B6RSOgAb2yZtZ+0FzjCnKjQT5AbQfXGTdjcCJNp6E0bcvVcbpgxx7JlzvXKaTRCL8Q+6YjkeswqbmAz7PhTbMuqHkjsJ4sXCeR3aAVb2xcxtvRe8vVMyrY2Jd1I7t3rTSHSvBhIAX+M42yLn+4MEjiShubNQ4Ts1IaVX2jjB+kAlu0WvjZUdfZNB2CljD9BsqeV033SC5CSr3Fch5AuIi8aL4Mf5CfOWP5lgSwtcW7Cehbs05v498bRrKUQbmLk/vsDpI8K1kR32esJOUT7xFm0xA/FmJGGL5oeGeY7arDPlqGi8tN5MVKz05gu8vWZwWbnwq2y/+mxVnR6KloLN+dFSz8AHOdVxFFKms='}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('demo.brd', r'C:\Users\user\Desktop\demo.brd')]


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
