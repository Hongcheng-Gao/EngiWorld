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
