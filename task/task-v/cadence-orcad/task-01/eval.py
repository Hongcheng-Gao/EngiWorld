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

BUNDLE = {'_common/README.md': 'eNqtVMtqGzEU3Rv8Dxey6AM/2u1kUYLdQCElIQ6EUhdLnrn2qJZ1FT08NWTRj+gX9kt6pRm7bmi7ihaDfXWf55yrMxCLkrZbMmMBP7//AF9LhxXgTuoogyIDVsftUpl1v9fvvd+h20OQfvPCg0hOI7sXbNAbD4Eg1AguGsPucO0mF1OYSBuiQ9gpCaEhWCmNHmp0WKSEj3DJBvjjPMItPbU9/3lMxYdPD/zF9vynLS4acht0o1BqcZhck1kPtdoxBXel5r9kGVQZoJGhrBk5sWijFg8RI47FADxFV/KNNHsQr9tsX2kJlSNrOY8yA9jSDjNBoiLDUV0DTNVCmUXZcpSpfISbfaiZ9hq1RXcOjVMhxTKzKevd5GrAzajgYUUum1kTlSpDpjbVkFxWuv9D3++dncEsSBeihZdkSgSudlSLR+9Ze6+SoxCi32uHhGkx1lRKnTAYkytlNU5i9OODiH9D2u8VBZq1YouuiqK9KAqfanZJ+71PFFnxFHXFJRHE52MEtAFfIAdgdd4ykIT97yZOqREMfIZnwp1JU8G9MhU1I7hCucPjpGTRjDo8brvNYYoOO9atWIeDpQadZ2Z4umkxl0aWZCo5t5myEX5LCM2Pzc1zc/PcXP4O37yddxmB509csL+VoZ4HmlMMNoZFpdwRnzvu/xCwRoNOJi1I8FupddICLDUtB5An9qBCp40BpImtU4Z1Im4uZjMBYxCXFx+uBDQq1FBhkEr7w+j39Z7Ttvi1qudS/Eok8RvQMpoW+wNsSSw8pX6X4jtjnt/hQ1QuNzmRFSZhXW+C5Jxr5oN1XVIiO5E64N/Gx2121qpE45GVhrxtKb0y7MXx7Sw1h3n4OBter1bsOvRhz2pf8/RSp3QBRzCzqiWQNS3BYNPvWUe8mz4nPHlTmyy5JUI00cul3oPX1ORC7VWtQhbPSVtul3PkB1htudw0LXgql14K3k3G3/D6JfWcPCNsQ2cd8pezqAp9QMsTM3+0ym8Lc/ALEa7kpw==', '_common/run_in_capture.py': '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', '_common/worker.tcl': 'eNqtVttuGzcQfTfgf5is5MAu7JWToi9boECRFEgLJC5sA3mQFg61O2vR4pJbkmtFMAT0I/qF/ZLOcKlrLNsoohdJvJw5M3Nmhr3ed/wcHvRgZuwUbeoLBfDv3/8A4L1QrfDS6LgHypgG/ER4sK12ILWTJYLQYBrU8E40vrUIDp2jS4TJsB/MDLwB1GKsEKSHY6PVHDRi6XhjjFAajWB0gdCQkR2Yk4xRAN6kcOWF9fA+GxlbiHLkjVFuNJZ6FK+k+BXhWJlbYgaygkpa58HLGk/SDuRtChdM1U8QrsnRd6auhS7hs9Ql8TyO32e/7Ows7/+Ywp/CeYycwseZ1hL199lAmUIoDtUgEBx44aZucFMQlNGDdXw3LmcZ6ltJW6rMsu5Eljn2M4bvgsNC0dZS354G3jEXjVHKwRNmu3M3f7XYIicT7ZwB31JgC6NLlwL8qufwQ8h4JSk5lWnJY7JB0ZcuOlbCccyz9A7MTIMWNbpGFMhwlbF01qigkxMQHYCG2tzTVcovU04HnOIBuHZcSkuGr2lxCe8KKxtPIAxnCdmQuXGgY2FmpSfPg23yoJSFhz+uLj7BWBRThi+lmwIJUkAj/ARMtaTJaMXEGMfXj1nLaTOHqTYzB7PgIt0mQU9Dbvn09Tq45H2JSo7RCo+k1lpqWQuVAWhD0vV87JR/41ePVgtFP7A4hbvWceLgS+fcF+bTOrRnrm0aJclbVp3sBBizuhJ8Y01Bmo/hoZwqtAy2JH8CbmJaVUJFtcOVFArJW7K5CqPj9YlwIXCe8kDRQFWxi9+3XxwerGQQGsVjSoaHwwMW+b2wMlR/0OINSQCSl+k22QFgGYX7LwUIwttFWQYe4Hxnx8tielM7bjc/ndPmgh3lvDxRqPCw+MbRaKFbpU700I8rq6P8aVrKVzIarpCj/HIQyqIo50ucZH3HImlFd/8X+8K7J2rdcij1espR7O/c2NzavuTQr8L2plvazz6EBcufYSZ8MeEra0PRFe5eLwgvjZvnorvJ7Px5ZoRokdhwzSTPMmCazzLYVc//ygqL5NWGSmKiIRBc+nlnxg6GyhlS3fBWmTGcaUPjpVGCesqZnzfUNWEY0nhnaKm/UXGh0Sd5nsdcG5JYMWFM6AfgDWWyMa7viOWFVOFQvn2EEl03MCyoEKcMWFMjjv/ikMnhLK4nRx+yo4/Z0VWSv6QCRsN+QM+Xsc6gz4ySbQa2IIOssk32/GkbRSNPQe+cAibpGRDH9I4XC0BrN/53tVosduH2EwX47fLy4pKbeiBIPAky2b7eg8/Uj8NTKaXdrtA0DY/lhOQs8Lzzq84fh1tBc9Sm22jsOKFQpp23rPtaUJ0kIb+QsIFksaWCVdsMDPP8W7iqhGF4xPUD8Cx/xP0+HeLt7S1Kt0Pe2wjq+mcPPpIDKxfZJ34JpNtZLKkcnyK8Ph1z3QWQRjRSUFlhnNmAsthz1mLQ8/JsUP3mhfglKprn0F/OgU46e1tDHhtID36vyEd6NQRb9G3xLL5vTnmu3/P7iQriHrVEetGR/6y0odQVvyHIiHvcShR/Dq9fw6v+U0dWkt0vVWVEiWVKDw6lnhpo4VV+K3XaNcj/AKnJ1W8=', 'eval_inner.py': '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', 'ground_truth/FULLADD.DSN': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('FULLADD.DSN', r'C:\Users\user\Desktop\FULLADD.DSN'), ('FULLADD.OPJ', r'C:\Users\user\Desktop\FULLADD.OPJ')]


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
