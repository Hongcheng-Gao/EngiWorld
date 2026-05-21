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
