from __future__ import annotations

import base64
import contextlib
import importlib.util
import io
import os
import shutil
import sys
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

ORCAD_CAPTURE_PATH = r"C:\Cadence\SPB_24.1\tools\bin\capture.exe"

BUNDLE = {'_common/README.md': 'eNqtVMtqGzEU3Rv8Dxey6AM/2u1kUYLdQCElIQ6EUhdLnrn2qJZ1FT08NWTRj+gX9kt6pRm7bmi7ihaDfXWf55yrMxCLkrZbMmMBP7//AF9LhxXgTuoogyIDVsftUpl1v9fvvd+h20OQfvPCg0hOI7sXbNAbD4Eg1AguGsPucO0mF1OYSBuiQ9gpCaEhWCmNHmp0WKSEj3DJBvjjPMItPbU9/3lMxYdPD/zF9vynLS4acht0o1BqcZhck1kPtdoxBXel5r9kGVQZoJGhrBk5sWijFg8RI47FADxFV/KNNHsQr9tsX2kJlSNrOY8yA9jSDjNBoiLDUV0DTNVCmUXZcpSpfISbfaiZ9hq1RXcOjVMhxTKzKevd5GrAzajgYUUum1kTlSpDpjbVkFxWuv9D3++dncEsSBeihZdkSgSudlSLR+9Ze6+SoxCi32uHhGkx1lRKnTAYkytlNU5i9OODiH9D2u8VBZq1YouuiqK9KAqfanZJ+71PFFnxFHXFJRHE52MEtAFfIAdgdd4ykIT97yZOqREMfIZnwp1JU8G9MhU1I7hCucPjpGTRjDo8brvNYYoOO9atWIeDpQadZ2Z4umkxl0aWZCo5t5myEX5LCM2Pzc1zc/PcXP4O37yddxmB509csL+VoZ4HmlMMNoZFpdwRnzvu/xCwRoNOJi1I8FupddICLDUtB5An9qBCp40BpImtU4Z1Im4uZjMBYxCXFx+uBDQq1FBhkEr7w+j39Z7Ttvi1qudS/Eok8RvQMpoW+wNsSSw8pX6X4jtjnt/hQ1QuNzmRFSZhXW+C5Jxr5oN1XVIiO5E64N/Gx2121qpE45GVhrxtKb0y7MXx7Sw1h3n4OBter1bsOvRhz2pf8/RSp3QBRzCzqiWQNS3BYNPvWUe8mz4nPHlTmyy5JUI00cul3oPX1ORC7VWtQhbPSVtul3PkB1htudw0LXgql14K3k3G3/D6JfWcPCNsQ2cd8pezqAp9QMsTM3+0ym8Lc/ALEa7kpw==', '_common/run_in_capture.py': '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', '_common/worker.tcl': 'eNqtVttuGzcQfTfgf5is5MAu7JWToi9boECRFEgLJC5sA3mQFg61O2vR4pJbkmtFMAT0I/qF/ZLOcKlrLNsoohdJvJw5M3Nmhr3ed/wcHvRgZuwUbeoLBfDv3/8A4L1QrfDS6LgHypgG/ER4sK12ILWTJYLQYBrU8E40vrUIDp2jS4TJsB/MDLwB1GKsEKSHY6PVHDRi6XhjjFAajWB0gdCQkR2Yk4xRAN6kcOWF9fA+GxlbiHLkjVFuNJZ6FK+k+BXhWJlbYgaygkpa58HLGk/SDuRtChdM1U8QrsnRd6auhS7hs9Ql8TyO32e/7Ows7/+Ywp/CeYycwseZ1hL199lAmUIoDtUgEBx44aZucFMQlNGDdXw3LmcZ6ltJW6rMsu5Eljn2M4bvgsNC0dZS354G3jEXjVHKwRNmu3M3f7XYIicT7ZwB31JgC6NLlwL8qufwQ8h4JSk5lWnJY7JB0ZcuOlbCccyz9A7MTIMWNbpGFMhwlbF01qigkxMQHYCG2tzTVcovU04HnOIBuHZcSkuGr2lxCe8KKxtPIAxnCdmQuXGgY2FmpSfPg23yoJSFhz+uLj7BWBRThi+lmwIJUkAj/ARMtaTJaMXEGMfXj1nLaTOHqTYzB7PgIt0mQU9Dbvn09Tq45H2JSo7RCo+k1lpqWQuVAWhD0vV87JR/41ePVgtFP7A4hbvWceLgS+fcF+bTOrRnrm0aJclbVp3sBBizuhJ8Y01Bmo/hoZwqtAy2JH8CbmJaVUJFtcOVFArJW7K5CqPj9YlwIXCe8kDRQFWxi9+3XxwerGQQGsVjSoaHwwMW+b2wMlR/0OINSQCSl+k22QFgGYX7LwUIwttFWQYe4Hxnx8tielM7bjc/ndPmgh3lvDxRqPCw+MbRaKFbpU700I8rq6P8aVrKVzIarpCj/HIQyqIo50ucZH3HImlFd/8X+8K7J2rdcij1espR7O/c2NzavuTQr8L2plvazz6EBcufYSZ8MeEra0PRFe5eLwgvjZvnorvJ7Px5ZoRokdhwzSTPMmCazzLYVc//ygqL5NWGSmKiIRBc+nlnxg6GyhlS3fBWmTGcaUPjpVGCesqZnzfUNWEY0nhnaKm/UXGh0Sd5nsdcG5JYMWFM6AfgDWWyMa7viOWFVOFQvn2EEl03MCyoEKcMWFMjjv/ikMnhLK4nRx+yo4/Z0VWSv6QCRsN+QM+Xsc6gz4ySbQa2IIOssk32/GkbRSNPQe+cAibpGRDH9I4XC0BrN/53tVosduH2EwX47fLy4pKbeiBIPAky2b7eg8/Uj8NTKaXdrtA0DY/lhOQs8Lzzq84fh1tBc9Sm22jsOKFQpp23rPtaUJ0kIb+QsIFksaWCVdsMDPP8W7iqhGF4xPUD8Cx/xP0+HeLt7S1Kt0Pe2wjq+mcPPpIDKxfZJ34JpNtZLKkcnyK8Ph1z3QWQRjRSUFlhnNmAsthz1mLQ8/JsUP3mhfglKprn0F/OgU46e1tDHhtID36vyEd6NQRb9G3xLL5vTnmu3/P7iQriHrVEetGR/6y0odQVvyHIiHvcShR/Dq9fw6v+U0dWkt0vVWVEiWVKDw6lnhpo4VV+K3XaNcj/AKnJ1W8=', 'eval_inner.py': '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', 'ground_truth/CUSTOM_LIB.OLB': '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', 'ground_truth/parts_spec.csv': 'eNo1x8sKwjAQQNH9wPzJLMbWR7Y1qRDQJiQI7oYuSiliIzX/j4kgd3Ouf87D+JrITJ9lXsecNvL6LJeU8ntb1owQ+sh7bihQkVQi6M7zkVvSVCSV8jgFBDsYVnygKxVJJYKxzvQSnaHS37JrWgTnu5tXdKforBYlv0f4AkrXJ6c='}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('CUSTOM_LIB.OLB', r'C:\Users\user\Desktop\CUSTOM_LIB.OLB'), ('parts_spec.csv', r'C:\Users\user\Desktop\parts_spec.csv')]


RUN_IN_CAPTURE_PAYLOAD = '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'


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
    helper_path = root / "_common" / "run_in_capture.py"
    helper_path.parent.mkdir(parents=True, exist_ok=True)
    helper_path.write_bytes(_decode(RUN_IN_CAPTURE_PAYLOAD))


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


def _call_inner(root: Path):
    module = _load_module(root)
    func = getattr(module, CALL_FUNC)
    args = [_resolve_arg(arg) for arg in CALL_ARGS]
    return func(*args)


def _apply_runtime_env() -> None:
    os.environ["ENGIWORLD_ORCAD_CAPTURE_EXE"] = ORCAD_CAPTURE_PATH




@contextlib.contextmanager
def _suppress_output():
    sys.stdout.flush()
    sys.stderr.flush()
    with open(os.devnull, "w") as devnull:
        old_stdout_fd = os.dup(1)
        old_stderr_fd = os.dup(2)
        try:
            os.dup2(devnull.fileno(), 1)
            os.dup2(devnull.fileno(), 2)
            with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
                yield
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            os.dup2(old_stdout_fd, 1)
            os.dup2(old_stderr_fd, 2)
            os.close(old_stdout_fd)
            os.close(old_stderr_fd)

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
        _apply_runtime_env()
        with _suppress_output():
            result = _call_inner(root)
        return _is_pass(result)
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    print("True" if _run() else "False")
