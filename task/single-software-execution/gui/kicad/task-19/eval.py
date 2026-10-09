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
INIT_MAP = [('board.kicad_pcb', '/home/user/Desktop/board.kicad_pcb')]


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
        if isinstance(result.get("pass"), bool):
            return result["pass"]
        if isinstance(result.get("passed"), bool):
            return result["passed"]
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
