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
INIT_MAP = [('NO_TEAR.txt', '/home/user/Desktop/NO_TEAR.txt'), ('board.kicad_pcb', '/home/user/Desktop/board.kicad_pcb')]


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
