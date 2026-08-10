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

BUNDLE = {'eval_inner.py': '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', 'schema.py': 'eNqNVG1u00AQ/R8pdxjMH0eAW/HTUlAjFCQkBFXafyWyFnuWmm52rd0NIgqWOAQX6RU4Cidh9sOx06ShjiXH4zdv3ozfOEmS8Wj+nYkFmrWwYMpbXDH4++s32FsEY5msmK5Ao11rCXbTIHClgQkBSGlrZjFrNpSn68aabDxKHCPXagUVs6wUzBg0UK8apW0fegm8RlFFJNHW8msHmsnNeOR+Fzv4eOQv8PYWy7sgNR+PgA7JVpiTTh1uG1euyuGLUiJE8EeDpXUx4oUpfFQSwxNW2jUTh3GrBGomS+LlQjELP/3DPYxUNpSlqGs4RCvkUBQULYrUoOCTKNIdNEq7Ng5+Obu6SqDm4CBZUAwoDELybvb+Q9LnNExbl3LDk5ttIGiXsPV5rvE2WfbgjrBrGGrjZHrRAx073ow1Dcoq5UmXMd3uEbTJ5JA9DO3p3AEfmcPNM32UeTf2p5NTyvTP/XY//Si5f18nudLtDthOhhTR+gnQ+cJfsm+qlqnPnzzm1H6nYlnLzF1RVwOvGotNwWsx9G/pDG5yELWxNwO3L8kFfmNS8hijQMFpmEpvpg4Z1aLWSgdX7lkW4DlNwbphXF3PL4EzKlqRz4HsXXXmvWi0alDbTe/l4M1gZXj1Bmpp84PBmPUqLTsbu29DSbgw9dDN5EQFqywT/ykgUKZPpDOl0tjT+fXNj6yIGxTQGZ1DGmA6hfMHDon1z7Pzw6YHq3s2oBl+CWgwK6Y3vRx6MYMKopYYl/uavBHXOtqkzeN9qNGebfsabXRJfD0AqW877pj/n2evObl4+UjrD/r0SvpNAJgvFp8WnQKfsbdUx17yKUrqOy0nR1bqs4y75OEE+AcnCfRs'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('mcu.kicad_sch', '/home/user/Desktop/mcu.kicad_sch')]


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
