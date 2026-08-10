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
