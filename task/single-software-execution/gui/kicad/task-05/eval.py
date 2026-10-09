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
BUNDLE['init_file/design.kicad_sch'] = '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'
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('legacy.kicad_sym', '/home/user/Desktop/legacy.kicad_sym'), ('sym-lib-table', '/home/user/Desktop/sym-lib-table')]


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
