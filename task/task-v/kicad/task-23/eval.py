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
INIT_MAP = [('analog_region.yaml', '/home/user/Desktop/analog_region.yaml'), ('board.kicad_pcb', '/home/user/Desktop/board.kicad_pcb')]


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
