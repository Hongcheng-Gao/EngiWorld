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
 'init_file/board.brd': 'eNqtl01v2zgQhu8F+h9YHnpq9GXJVrFxiq1jtAE22SDJFuiRlmiHWEoySMqx99fvkKJoOUkTS81JQ3HeR8Ph8EOnX7YFRxsqJKvKKQ69ACNaZlXOytUU12p5kuIvZ+/fnX44/3t29/N6jihZcYpuf97ezS8RNi0vVznWTk2fo028CfB0Ry7IAxC1KalSYMqOjQh/IDu5oZmqxLIq1RTvqMR+1wWgimWEK7qF7nrd9Ppd2kqwHOVMKlJmdIoDbzxKMKpLpvTLKS6KptVYUu04eHFWwqdQUXPF1vpFiDVjzcluissKQ2yqywxC82pPZWV2717ZpokNCJAIZ6GyLhZUmA+UpADYXbXGKKt4BS9jjJaMc9O7YZItdCg6CYhkim1oJyOPaOMW97VSqiocMRxMnLTEa5JLx4sG89KW94ORt+B9bnn/lKKqFc0dczyUGQUt85wVtNTlu09kMpjqplpdc5JRh5wMJkYtcfFWxMTFeAUP+QZEVz/qB+H1a0izxl4huhlXt6qzaBxv1I8Xx262Beh/P8DYJfF7xQcN2N/vFouKiFwbsAexUhsPTFC0DWH7wWjXPLYRVLtuRqb5wHJ1byzDMQXtH0jHz2vjXuLYqnuJn9e+JPXdyDlbCCIYlfvGzmZaqnphzpY1yf4lq8bF2u3sXvyVNscPlZlgawXL+uz84vok/YQiL4lRUaA1U9n9qd/1MJzcMmDmtlN8MvJSsHbOyoWZ18BL9XEBnspsTd64GcFeHzX60NPLYoB+ZPSD5bGRD44+OZT3VI8PY++pnjzKXE95+mjijpLr24WRJV6QGhlUp2T/0XYYbaUm+OzjSv1x9efl/NTXqqZum/J7WomzQCseVeINgQg4ygj4Mrj5mKLsUZMuM0FnXOPDcUXP12MPqUtJZAShlwzMiN9dqL5dzB3brnKilGALONal+fwGOkipcrps2hknUjaexnR7sDvBwZXAba67v7RDtNtLhwE5ZqtS1Nx+jtQwEfpSIUyTcgrXASU7tv3KxQxmwQ7CbkbIDtBuPGijT78p/ja/mt9czJqVFDRJhByKCm6LNzakQ/Zs9Gu0qaQWHQZBabiJF9giD14mx73JgUVHr6GTvui0DTp4gva7idczRHjHbK+Ts5lZUxn8McCBKugSWZmdHqh6vQ/4v3LSeTY+0Qs+8RE+yaGP34T5JOBvV+dHBBwfEXB4RMDhEQGHTwL2O9n23VXE7/zA+eYvD6z/AVN4Ndo='}
CALL_FUNC = 'evaluate'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('board.brd', '/home/user/Desktop/board.brd')]


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
