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
 'init_file/amp1.sch': 'eNq1V9tu4zYQfS/Qf2CJ+qmwSClR7AXiXWzdtFigucBJiu5TQcu0Q6xMGRLl2H/f4UWkfOnGVtCHxMMh53CGczQcXn/aLHO05mUlCjnCcUQx4jIrZkIuRrhW8/4Qf/r44w/XP/12P376+nCDOFvkHD1+fXy6uUXYjKKZmmG9yM55tEE0ADw9MSvZKyBqseJKgVi1ZMTyV7at1jxTRTkvpBrhLa8waS8BUCUyliu+gel6ZWdJG21RihmaiUoxmfERplGMUS2F0qoRFjJ7seNGrtQ2h3W5kLAZWta5EiutADMwWeVsO8KywOCdaqPS2Kj2kZ3KDY13gABH4SUk6+WUlyP8ARAkWwLaHVewdVbkBagTjOYiz40Da1GJqXZGHwRimRJr3jqVPbykwfu1rioeEOPOiBcN4oOQb3hojugNuMsG7nG7nBZ5QLzs7GHqzxD+B8BBZ8CrBvAvltfdEEnIeJW98CUDyqJNyec5m3JA6P3euyO9x6g37k2wmVixEijjdcYtMS1ZKXgVBlvnmaYqK82qFcu+sQUsuiZe1Nva8w2is7x/+Hz7YAxfRcnRJh7hfhrRIUZbEK20SYIyiK9ipl4075MUkmUCNAklb4MFLNoBp98FaCWki/jLXR+MjcW2Qci5XGjbVSGkOjT4pWXQP8Hi/vnJWDj3jOmuASoLSO8kHtKmXpmktESTqhlfi4xDLdsduW3+vL1IAX8FdBGw27NJ44IpnXz945Z9hopmIJtsh2D07tfEmoQNPjrB2WNYYhVeMKuJ92d3ZCcdQQ+5WmZ5F6JO+jfPuzyNo2TgGGFFzYiLaBg7mlrlafRyZv+F1Q0qIDlXz0QKAR5DOis+anFo988m3qHN9/mfdGf/Ts7Hp+W82+kmkZ7dg3LKM6HoAQ59D2+6UvA9yXKB/1+lSn+9/4RSBZdcXfFyrS9Ue00eL11//ByH4mUqwJm1iyZ0QGJ6Wgnbd9rQz/s87uLzuJPPaR/+/qYpfXfpJTtNA1OqFNPaeExaA5hawyIm1YzP9Vx7BJNZznT76EXfG9GmNYKVDPrkQFBolUvTHDWsaWHo3sYLDuAZDs357dsZ5OPyd53VwJ1E9uwnbXt9xbSNHfsa44YUyOUypt8O8Mbfw7NZDXAhXwGSShe4j7Z64bwlmQ1zJqS+AM0vKKCpNu+Jqj1AthnUR6SpY250XV9pZOurEcgRi4m3MKQEm0saXdnv/DKNBknzcX+gR+3HB/ZXNNL9sLe3Ie54PTVPDQjKCaCSLm7pP60vd9BGa0Zogtjn3GLJpXKlCT65Y0HDjG3HyMG6vVDNynivwjbBxz56cxnaY0y80tfYOE1aRTb2L0vvKZE2jSEu0/l1DEzbHgY2PiGwNI2GTZNtotFxNanyIZ4fF2kSRzxjSWAx8U8ZW4TCU56Y9z5I/wKp8a5s'}
CALL_FUNC = 'evaluate'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('amp1.sch', '/home/user/Desktop/amp1.sch')]


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
