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

BUNDLE = {'eval_inner.py': 'eNqVVE1v2zAMvftXaLrMWht3K3YYgrpAgHXosRh6WpypqiW72mxZoOQua5D/Xkq2ExfFCiwHOxIfHx8/zAq6lnBe9b4HxTnRre3AE2FM54XXnXFJMt79cp2Z/oNKquBphX9o9P3kdoPHJLm++n5F8nhIkVo3SMwyUK5rHlXKMitAGZ98Xd1e8YgElZVdaxGYAl2vFj82a7F42uzO9+TFqXAnhdx9OsX7QhZyeXjgcfd5T1lys7q9/gdn4FierX9eXL4vaOE+bE4QnyRSVYSbDlrR6CeVerX1S+I8MLK4DO9lQvAXrpF0lJy5/j6lF+F0SU+jkc1ho4oIa0R7LwVpl0M92qyGrrfpR8YyI1o19waFTTDxAqtlG1GqlBZQGIxB8cky1KNtOslWj6LhXe9t7106vLnUcJQvdekH/YN1asoRO2tLxAnjEDSizwh1fZv5rafRWAeC2Fy0hDSM5B56/0BfQVF+mIec7KgVztEl+SYah9nSY2wahY5i2D766Yrg4AUZmdpqh3mxIYEj6ZqCEjiKdIP0FVVbq0qv5CS61c5pUy/JLpCEEu/pjCFWeCCaAs66H1yQHdPCHqTKlJ1Erpz2vlp8wS4ogA5cTnWNPooyRt7lc/9DoNr/F0/0ezvTUN9WwF8iQfxBsqnEUleVAkfi53goxqppFHYoXCDorQJMoWKbQqBb6NULS/mgyt+DbU3vxrCLR4KC7g5VFx5hjojKK4hb4UwKr8hUmrhK6CZ5rQHXC7aAh0bh+skxUc5boQ3ndKjHtJGgxr3hVDLMqUU101W2grpvcaXchBNMo2wzISUXoy2dT96IgDpMOwIjTYC60dmCRpew8TLZt9alL761AMxmH9Ep0UZijPwcW2tc2KTClVrncegZS54BYmzAPg==', 'ground_truth/sum.txt': 'eNqNVltv4jgUfq/Ef/DLSkFKQ+4BtLsSBWanmlIQl+3sU2USF6wmNuOYdthfv8eOQ0KLVtNKVY7P7Tv3ro5FgcUJTQR+p2yHluTAhezcTIa9nKc4f+fitTdlOwofedZzZHF45iLF2fNB8C3x/F5GCu5sRda5mXGGRgeB/AR5g6E7GIYh8l0/7tyAPWN/JbGkpaRpOezcIPipGdOfkjBZIvT9wbr1o9BJIj/oIvSPIt3EiQehIr9vrMCLnb7n+Yq5sfxw4AzcqN815mhBWEk5KxFlqKB5Dg+SiBK9U7lHIcpISguco0OOU1JWSg/4BBJDhNZc4twKwfKSHyXAspSXRY4ZKeHTuCAl3TG03tP0Fd5Bz3WSwIv8trtKdIHTV7wjaHUqtjxvPHh+DHZnVAguSGbFCVDTYkuyDChXuaSstLww9ozPGUn3mFEoyCdbQdvSWTcwil+4KLD8DKCOZTnWJSFDNN+s0fwLmozW04Y3VXZBLayeVntoDsWAmKuXJ0zfSHbxtMBZKSFwSNQLZVSqYoCFxFg9MVzQFJV7fCANIAV8fpTP/OU5AzhAG/xHlhoLCI1KlXkI04uU/Ibh+kGRJrKoVl3w/IT+phhZB/jbRSsqtUO36kdVq2sNOQPMxbFAWgKU/iXISouuUnSgL13XrRsX+JdlAFsswyJDj2NNPwJu83QO6CvPNQpoKmmAg9itIeuyzY65pBWCOp0GuuJCONrxXhy1gbs79aI/ZzQV/I1iTXyd3Gu/nZsxZ4zoRH4OuOEpo0+9JZalFbp9jayimvSq90ptlAuCs1OtTrJG2b2qWmdgRqFqkPkLv7/sdoLZLv+gjqwVISjnuxeak26Tp1bUY14ccqI+WzAd1/2t7c7QBq6hDGjM9rBcVDnTc0N4SexEke9VImsBGwU9ELaDRWMkWp4+OLrwY2J7PMIOEIi/1BX+pXwqWXQAvSbc//f8ye9qNkEH2BrVjsQS2m0PQ51CnpuJgSUJO/Fa+xQHztTurro6VfOp99uGHQzZTKefdD+ooXEOY6z93I8trXg/12FCulMB29TyXGWh2YHVtpB7Is5JeCSy6aIouJqwqJ4utSGblou9D9IbdiwB9WAQtoPwmyDCqI5i+uNI33CuwrgfQx96Ko/oD+T1vBBN78e6S1yzPcHBujXF6sRA1b4RonRMwyCrD6cu7ttw8RI1DNsTWA0ctz/o217khGFQT4IpCIYxRFb5A1UG/MQZ9M2EvhGhro/AMr/oSthkDSS4iHAw5Ukxe2czsRN49aLjx21ObksKx0nZuq4QOF4UNX3SgxzDAagEm57RbCJsg30E2H+/W/5p4NtNL9mqRrWYsdNI9lRq7ZYLzVItbAB1btT/E4JBtQz8lYLftaPIGcQ29KetrqvtOlEQ237seC7cp9YJttV42PoXPsxfOBv69ts6yW0rPlQs8h3fC1QKzCZQkV7OSxX8WM9Vb4xFWtorfQetN06zsmsvYX7VgiMQuxYaKZk1+SlbubFUbiDE9Xyh8Gm0+jcaWEkSAmcxf5ouL3muHpW/HifXnu/m6/V8dsmJEyvuJ90mnieaQQvdnarAztHoZ2j91j8/BluNo3J79qIs/gdEnO5w'}
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
