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
 'eval_inner.py': 'eNqlV1tv2zYUftevIDQMllZHtVO0HbypQxcrqZE0Th1n7ZB5hCzRNhuJ0kgqTRHnv++Q1NXNOgPxi0XqnO/cL/oBBecnk4/T2dkYz4Kj6WyMJ+fz4GQ2mf+J528vT/HglbXiWYowXhWy4ARjRNM84xKFjGUylDRjwrLKu88iY9Wz+CoMax7KTUKXFd8FHC3rXTALkK8PDmDTBJBdjxORJbfEcb085IRJazadzoFMUVdXdIWE5I564yJQAVGmZHlKzMhC8KtOHmWCcOkM+g2Ha5X2UCYJZ2GCGdhwSyrtyG2YFKEk5TWOs8iygk8XwdE8GOPjyZnS2t6EnBEhsNgQIjHLUgpI3mW0GWeRbc2CD1eTWTAGymutkD0nd9IfDm6252FK/D9ABNleMfpPQSZjf352cfpuevrB7reIZ0RQITOOgAs9e34w/BENDwev0OHLAUo/GpyjLE3BIw3S9N3p+GR8fNlBevni8NXwYPD69fA/uN5ffZx/Or06Ba6FdTyd/T4Zj4PzHeUPD5+g/MunKz/YR3nLiskK4ZzmBHMSZTzGUVaoQDsqH1yTHjr+UZYkJNLZW4X+yJBqmvKKE0sfDZhQPlkYDDAu2hTsRmWfTmItABI4jPHyqyQCcljkCZXO0v7rbjCwS+EafIWW9tauktfgAODS9r+9TAhz9MFFv6KfGxD1izImKStIfRmDnjGJQU/N4pmzYyeQzGxo9xHhPOPCt+maZZzYbs2ZhjLaAB8nniAhjzZORxK3nd9GpkNsZ9oZ23nwab5VQdqOIdxrqJeM6yDVwdlOvzDCJywmd1t7B+6MLmdkRaCiI7KtonqpyklDHENDUA+uf/23ct/ipzItdixtLhtTymB5YZ4TFjvaMm/NsyJ3Bq5yvrGVJIJUMG4ZZehwrMoDp8Rxq7TiJE/CiNQpVb7vo/KFMkHsmWOaiNzl8FqHq5Lp1tll0PtIS1MZUZlFJUkhu5pMkDxkAlhSjWTI6pcKKksAh5EvBqXRtZtMXZjWySt5nAqncXVlwXWLfIGe+UbrtlMrysaZujxVF15zKr86lFGJVRH1YbKIL4SXh0ecq0mbkny03ms4o2wJ+T9MLcHuboS+CX9bix01rbLKG3Z/R4NRK1u1f+a8IH20ssMkQfeiSJ0uvafGkmoq7gMqB5YyoG5MOUxOwm9BFLmLSC6RDPmaSGHKLqVCULYGKxLoy45T63Wwo5brkcTYAJKuRy8WpRcgvDXzjisPaisfZy7tOw6h3JSBpfaGXWmmq/GXSkf/vnx46Bu5/r3+e7Ahcybnk3k1g3tLnt0QhjujuBzBPRjBF2dvj4L3wfn8UnVtp7fXFOv1UW+vWd1z+6jEfNKwqwU+ad63tNl7YNaS994Pem41YdWShLNC5gXE2vzjmHIXHbxBMY3kqIy8bnn+YztVM1308GxhNB29s3U119V21W/3uCWNY0iGFQ/XOgP9eo8xZHVJqvFqFPOgPhw7D4Voz+YyXQ1Ju3WoplAtrG2Tn3f1bBpUyaAX3efI1ndqz7XhVCdyW62ay6NCUzodvZRC10bfBeDqgvrmNewfsIJrgpUWiRQQKlh4G9IkXMKzmgh124U9gUQ3I3RfC3+wv+ML4Asj2YexKQHOdMU9+3i7Il3rUZMMutW1pwuv6Yz0rusU5+h77mgxde2y1BcFhtxM1ccNdGob4zSkDGPbAJpWWsVefVzAxe31cKGXCbWfVXcueoOGZrGowq72DhZjyQu5MZ7NOWjrqC8lLy7SXDidajLCoJ4prE0MOha0QSbUh1coIkp9HXb4ivkXJKhkIA==',
 'init_file/broken_harness_sheet.SchDoc': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('broken_harness_sheet.SchDoc', 'C:\\Users\\user\\Desktop\\broken_harness_sheet.SchDoc')]


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
