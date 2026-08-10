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
INIT_MAP = [('design.kicad_sch', '/home/user/Desktop/design.kicad_sch'), ('pinmux_initial.csv', '/home/user/Desktop/pinmux_initial.csv')]


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
