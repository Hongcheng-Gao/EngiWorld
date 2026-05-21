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
