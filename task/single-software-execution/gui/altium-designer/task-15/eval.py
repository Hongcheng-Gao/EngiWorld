from __future__ import annotations

import base64
import importlib.util
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

BUNDLE = {'_internal_native.py': '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',
 'eval_inner.py': 'eJydV+t30zYU/+6/Qsd7xB6OSejpOrIZTklcmkNJ2jQMRtv5KLGSaPiRSXJpof3fdyXLsdxSCMuXWPK9v/t++AcUjl4O344nR4NoEvbHk0E0HE3Dl5Ph9K9oun/6KuruWguWpyiKFoUoGIkiRNN1zgTCWZYLLGieccvSd//wPKue+TUvWddYrBI6q/iO4WhZh+EkRIE6OIBNE0B2fUZ4nlwSx/XXmJFMWJPxeApkkrq6ogvEBXPkGxeBCohmUpYvxfQsBL/q5NOMEyacjldzuJa2h2aCsAwnUQY2XJJKO3KJkwILoq+jOJ9bVvjuOOxPw0F0MDySWtsrzDLCecSv01me8CjLUwpY/mn/8Gj4wrYm4cmb4SQcAO2ZUsmekisR7O7s7O22O7vdzs0IpyTo52kKJt28yei/BRkOgv7g9au3g/6p7Zlc3c6Tbruz13mIa3h8Mh69e//6Dlf31x2Q9SDXyeHbg8PDV38C14V1MJ68GA4G4egBjR9E+brG3f+h8c52GltWTBaoChPEt5jL/HRk4N0yD1Sg53mSkLlK0yrG/byQwVc0+ooRSx1jLHCVlgoJUhLH0exaEO64ikSArkAiKf2YzPOYOHYCWmRd20OEsZzxwKbLLGfELjkKZUBEYw58nAiHEX9BsxgnicPsjXnO2X77PW5/6rSfRhePXECTojy0SPCSB8AzfDkaQ5Xun4ZuCcxAPIsjcb0mElrb1YR3nvf+vjm/ccvyDpzz+JHrPA/Ob27Or8DTP24nB1yboYRkjjTb9QyTvIYWVVj0nSyyJaPi2qEZFZH0qAeNg38kTB8YWSd4TmSguQ7bnZAoTk4/Ea98VDLVU2X3/STYSCv11xJLEH1QMPr5YSBDVx19zJZE6Fh+Vlfyl2IxX21Oi5yhqGGbbFKmqQ1SxVxSbJcXBtKXw6bgb0v3LVSTrPX2KefFTKZh7QnteSPWBzjh4KyFXTKiShsdbY5SgKHZsoc+c4gWiR3DM23Dye6tXeUQphmJwW0yj6pQop9NWvQYnHHldL0Gjc5CsGQD8gfq+E93H9ZaN3VDawHOgiaARJ6jJP8IeldgPX9noZXk5JLAjItZvpbxPbuwqhgZSe5BTynKkNZp6FNBUmgRtUowEWhapACjTYJicErOX0D73zraLG1a+eZZgHbBIXEjM/2l6hmGAh0XPKAF1BLvWuDj9ZpksePcV977poDa6SbkNz1eoqCyopKcC5kgBsBZb+dCOxugjcIEgzaVrhy09+3wyrUB8RXD2QfoSORqDY2exMk1yDSQbwH68z1sv7OoM1OCT1kB2E5dmVXqVxkPmwGNf69z0Eig7k+3KIdCa2YdR7aB9pGKFZSidieEgZG29hb4iZeksJ4MR8NptWi0Ziz/QLLozr6h94wW7BnHR/v98HU4mp7KfHVa3ze1Wx5qfd9m0oLmX0nZdsrXUrbdZBpSttwKDClbbj4tt1oj5NYX5YVYF4I75X8UU+ai9jMU07no6URRgyn40pJY543aHQwMb/OmsUbW19Wy6JlDYUbjGAK/YHipBkaw2dA8nShGcy8VU1VsrzHk0v1+XpKY01DOtGrVMU1+3NSznsGaQW3uj5Gt7mQF2nDaJK2p1oYLRo6idBp6SYXOSn0vAFcV973XsH7BN4UiWCiRZdEXGb7ENMEzeJbtebNooPmKzD/0dMFL4bf2V3wBfHgO3TCWpZzIFWDrzcWsPdf6okklutW0pwmv6ErpTddJzvveMtxhMDXtsuQnUgS5mcqvtQA+V6IohUYVRXbP2GGq2MuvJbi4POteuFK8nLzVnYueoS4iEJhN2JcM5geMCVaIVenZNZOTTX76+XGRrrnTqKZSmCvHHyS0CJ7Akpxx+SWJ+ZzSQIUdhs1/5eGhng==',
 'init_file/broken_harness_symbols.SCHLIB': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('broken_harness_symbols.SCHLIB', 'C:\\Users\\user\\Desktop\\broken_harness_symbols.SCHLIB')]


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
