from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\user\Desktop')

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

BUNDLE = {'eval_inner.py': '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', 'ground_truth/project.PrjPcb': 'eNrtV8ty2jAU3TPDP3SRbVOT9LnwghhI3BJMMCbJdDoZYV9ArSy5eoTw972STYJJ0yHposlM2YDv6xydeyXkrx1QdM6/NRsTkIoK7rf2vWbjhIIkMl2sTkUGPhqCBeEc2EiIfEByyuexXjHnGQEDokD1BMtA+rehZWGihewJmRMda4lp/l4g8kJw4Ppqr6oGtfJ9uAYWQ4EEMNe/ajaiAnhkdGG08lvNRht50WsYSvEdUm0pjGkOSpO8KKOsCQsQLAAlK+WiIC8YmvoiJRpXOiR6gXSHlMdLUhytrgagGZkCsyB3VvzlUBkTy6GQGqMsZ1fSGeMFgO5yLVc1V4GsM+cbmHwKciwsMMMY57dgVOkYNWGAGGt7B2bEMB0IPqNzIx1TPxZGpqCajUSBDDu+d9OrPrcJw3SKiuiS/YYtJVnZJSFRiI5ITY7aq4jbPlBsIYZb0hZ/3XWKPNnKpg3FEqRbtV3XmPxA2amQVJdeoxbdIBqLNudCO6q9qmQn1JCP4JramTpOkLPlUGCl2BSFBKUg60oppAr5KT6ReSlb2UHXmqrBr6rWNxt9MS/bWXXulHBMy6q4CiTkKTMZlNMX8mo6belm4+tQwgwkcNQSJ94+qYkVqsp1hi3SmLUWrYU569+OQp9OUS8K6k3FAQ37cbrALxyAW026nEwZZG6KSiPEmkg9IczAhhVDQ57BDfZeS8HWad5GmpnN6I2/YUhFAT6O4Z0psn32X9seiJLgKikydLi2iA7RZIqK3NkCRpQ6Bh4EbaPFBtm6w+7N3zgHzlnyGOC+/n3rMdDuZ3BZATNKI0fvTs6E058Gwsw/CaLz4/Ayqgl/sJPwOO3/hX+y8O2jThJ+/tKvCX+4LfxYFO5Is1OOjn8ttvcytT47DyfdZHJW0/rtttbu7I3NVK2wUP5MFH+h0z1Jupfdi/NRTfF324qH0XOT++Blyt23h8nFWa8m9/ttuY8EkZk9tp+B0C/12E6+hBdBNLqsKf1hW+nTIHnKQD+40g2sj/ewIBdy9Xg4z9sN8NM2YJsTJuaPBjx4GNCrX/u8bcQOTM2fAL2/EbR175qJ883xjoN35Ucv8nBXVVv37li4tfA94Emob3eW9vDhm133RkvylNv0Tsu9929bvmXgfRI3Iiz/cCo9srkY/gt7z03V'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('add_list.csv', 'C:\\Users\\user\\Desktop\\add_list.csv'), ('project.PrjPcb', 'C:\\Users\\user\\Desktop\\project.PrjPcb')]


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
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("True" if _run() else "False")
