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
