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
INIT_MAP = [('design.kicad_pcb', '/home/user/Desktop/design.kicad_pcb')]


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
