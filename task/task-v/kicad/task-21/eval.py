from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


def _push_utf8_text_io():
    import builtins
    import pathlib

    orig_open = builtins.open
    orig_read_text = pathlib.Path.read_text

    def patched_open(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        if 'b' not in mode and encoding is None:
            encoding = 'utf-8'
        return orig_open(file, mode, buffering, encoding, errors, newline, closefd, opener)

    def patched_read_text(self, encoding=None, errors=None):
        if encoding is None:
            encoding = 'utf-8'
        return orig_read_text(self, encoding=encoding, errors=errors)

    builtins.open = patched_open
    pathlib.Path.read_text = patched_read_text
    return orig_open, orig_read_text


def _pop_utf8_text_io(state):
    import builtins
    import pathlib

    orig_open, orig_read_text = state
    builtins.open = orig_open
    pathlib.Path.read_text = orig_read_text


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

BUNDLE = {'common/__init__.py': 'eNoDAAAAAAE=', 'common/sexp.py': 'eNqtV0tv4zYQvhvwf5hqD5JaR9nt0akXKIpsD213F92iQBEHMi1RazYSpZJUEqPtf+8MSUcP27GzaA6OxHl9881wSAVB8IuQomIl6Av+2CiutaglNExprqCoFfwkfmA5FKLkGqLkTmQsT3W2gUvwL022hsvpxL/lqu1EVZ13L3pbxcl0Mp38qFhVMQVCA4OfhW5At2vNzXw6AfzTiAP/zRfATF3BPxBGoV38GsI4dDpWYnW0UUJ+Ri10v65LfJBtteaKAn2yMoyiOOR1uy75xV9tbXgOD8JsYLUMVsBkjg/LFXCdsYbrBD5ZR85qjT/TianvuETJe+vZSRQ3rZLoimkoypqZSyFNQumYfYWPW7Op5XRSWunDptYcGVXaAC95xaUhLsy2QZ7KcousuGSQrSAIppNCYbZpWrTokacpiKqplUHosjbMYL201yEXSIaXfy+3xMJ0kvPCVTQy/NHMibMYLt4CwfGkY5yPpIFOh53g+L3y6YDZcDB1c1Hye15aB4mFSD4aWEBqvSgbKPbLib4TTfqgI7/gXTWJxZRSMBINkKZIxDloScpZBXXRg9VPQJ/EV7cGBTe3R9A+bLD1cVnAd1ByGaFC7GF464Q1DZd5NEwo7nSOMYC2XdqFkLnNWtY5n8GGs9zl3uX8h+BlDpii2lo2jnYSFslvhxX5Wc0wYtYqLZCdbUeIKFBbSG2YzLiPS377+aEOCew+GSnfvL6dueqQ0K/AYuGwdy7ob2uhk063TtMlQ3bRsbSigza2sZ/IsfqOnbjPHTIwJm4GKGJtiS2EOwFL/L6WvMfmr11HOwZzgSwZD8nyi8kqQzvKzQvL5YA+3ICnKfTV9mjc+nO5D8viM7ZOLdHO7OnpOOc+rtUa9N0Tkh1/96xs+Uv5e4cprCJSh/vYtph1fn+FrYhd6Y07uiS6GBcq7pikxqUIgG5pn8kYN9y3J2j0a/Lmza3LJiuZ1rtd7o0pwzTFY86kaaR5Wcygmyy9ACRKNKIk6WhZ4PJrCrBzuNvRJO07cePC27iJ4fzGo+pk6NFJbpz27VCOnGSJ0Lph2ARj4x6ubxbwZijkJdlSU4RX4RzgFTYP8prVlR0QkbInG049zQoe7zs+noLtuiFo+ArDLGV4AOAJkJofsFnjNL/r89wbqWOqHZDhZPXM+bBvF88UQDGBbfo7tf61UrWKglZiHBwBeGhff3gX9Fw+V6wnsqPw8Aa0FqlLhLbxCKszDs4wdmdx3/yAEl2N3HH61Pu90GMOcbdwvCqMauqy2dsCwyoOz82ucX5T7biyxyr1gmodq5jhqhKSUc0oweCI92FucfiS/TQ+sfvrvePf2o9uAHtF8CU8vwzBqTKs2+JgGf6nEWRBLJcvJkw+mhPePfgdfX+HOETsKJlBaOyjoceAHgN6IhT299/kM8dT5NHMKEwcf9lsDL60CcIw+bMWMkLw8XlDrcsyOxfsiV53fRQcajE7APZmJd1kdgUR5/SKv9SNm7I7kmC5n8qB88FekZC0KN4j/GDi9mOr1zoEfL7XQK9wzGzpU48rkfWM1Xa+18NhEhIC5xhvFyEfvV937/OjVbcfeZFVig9Oavz+2xPzx4w3plfGw0PeQcGk6HvTX92nk/8AqENGEw==', 'eval_inner.py': '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', 'schema.py': 'eNqNVG1u00AQ/R8pdxjMH0eAW/HTUlAjFCQkBFXafyWyFnuWmm52rd0NIgqWOAQX6RU4Cidh9sOx06ShjiXH4zdv3ozfOEmS8Wj+nYkFmrWwYMpbXDH4++s32FsEY5msmK5Ao11rCXbTIHClgQkBSGlrZjFrNpSn68aabDxKHCPXagUVs6wUzBg0UK8apW0fegm8RlFFJNHW8msHmsnNeOR+Fzv4eOQv8PYWy7sgNR+PgA7JVpiTTh1uG1euyuGLUiJE8EeDpXUx4oUpfFQSwxNW2jUTh3GrBGomS+LlQjELP/3DPYxUNpSlqGs4RCvkUBQULYrUoOCTKNIdNEq7Ng5+Obu6SqDm4CBZUAwoDELybvb+Q9LnNExbl3LDk5ttIGiXsPV5rvE2WfbgjrBrGGrjZHrRAx073ow1Dcoq5UmXMd3uEbTJ5JA9DO3p3AEfmcPNM32UeTf2p5NTyvTP/XY//Si5f18nudLtDthOhhTR+gnQ+cJfsm+qlqnPnzzm1H6nYlnLzF1RVwOvGotNwWsx9G/pDG5yELWxNwO3L8kFfmNS8hijQMFpmEpvpg4Z1aLWSgdX7lkW4DlNwbphXF3PL4EzKlqRz4HsXXXmvWi0alDbTe/l4M1gZXj1Bmpp84PBmPUqLTsbu29DSbgw9dDN5EQFqywT/ykgUKZPpDOl0tjT+fXNj6yIGxTQGZ1DGmA6hfMHDon1z7Pzw6YHq3s2oBl+CWgwK6Y3vRx6MYMKopYYl/uavBHXOtqkzeN9qNGebfsabXRJfD0AqW877pj/n2evObl4+UjrD/r0SvpNAJgvFp8WnQKfsbdUx17yKUrqOy0nR1bqs4y75OEE+AcnCfRs'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('board.kicad_pcb', '/home/user/Desktop/board.kicad_pcb'), ('spec.txt', '/home/user/Desktop/spec.txt')]


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
    io_state = _push_utf8_text_io()
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
        _pop_utf8_text_io(io_state)
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("True" if _run() else "False")
