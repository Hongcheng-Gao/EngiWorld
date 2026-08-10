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

BUNDLE = {'eval_inner.py': 'eNrdWN1u2zYUvtdTnOlillBHnZ0FKAJ4QOc6XQc0CZagGGAYAiMd21xkUiWpJMZWYA+xJ9yT7BxKiiWnSXextUB1YZs8/z+kzucwDPFGFEm5haU24IS9Pjh8AX//+Re8RbNCcLcazir3s76CpSzQJkEwXWN2bUEq0JUrK5fm0jw3WKCwmNS8xwHAKIb5mWegjROSXcAaRY4GLGZOagV4J62zoFWGCQmMY5hq5YRUlkgic8UWjlodr42uytNFK2tBVZsrNJhDRjJSVbqyxD9KkiPWdRjD5RrhVGwQnsGloFBcregt5rLa0OY7YaRQzrM4I8sCQS8BRbaGrklSRg++r0RhwZHOTBuDttQql2rVSi6N3ngq3pXkIbm14fTl5O/7CinAWk0krMXNVbEdWBjDig1YyquxbsjSCpbiyshMcIjEctiwxJT1M0XhsYXzrVtT8qwTKhcmh0JeGWG2IC1UFvMkCMMw8P6k6bJylcE0BbkptXEglNLOa7dB0Oz9ZrVqfxtsf9mtrZWUwq3JRKvhnJZB8NPslxlM/CIiK1TcNI0TSosubjCKk1IYVC4Igtmv57Pp5exVekFfb85OL0jq90GvLQbHMI8G79BYDnoIg1Hy3SAeQjSYitI1e/XGK7QZ5Xu3uaDPTrFGtS4uKdNfNsmGV0bcUrHsI1p482GLMO1EF9ywF85UGWey5u10DjNduLy3f5Hp0hOaMLpKR49r7bGll9tax2tUaAQ1FKfKdjmZY9QNs0tk3zzxUpfwMYYp6Vxps31Uw0yJqwJzTx99jJA+iGu07974Kfc88UftHDXZUx6OP+Hh+DEPxx/1cK9lxv2WOZfZNXwL54XI8OvsFh9hJ769ftmRYXrx7jN0zF49Dvv1eI2Gbvn/pxJvl6svWolubHtVqEnwQLZXg5POu+K/LsP3/TKcTukOlUXxdRaiH91eKVriFyzGUb8Yb86nB+OjF6Ovsxj96PaK0RJhdsfTyGeqxgcaZHJcQkpjjcVUKhk5vHPHNIOZGA5+gFxmbk6LIQ1j1s1dRSNhvaaPxWJx7Ke/dnQ9/iQ/D0kfvExWGZ6kvCn4A061QiLylyfzzE6zDc/i7FFiy0K6Qiq0UVwb5Yc3SIoYE8vzahTfk+QSaCL0HDt+b7ieqrHLyVykQRhnbyVNfuE8jGmkzGsCqrzZXoTxnrI6CvKBOeej44PRosfQpiax6CjToipc1AgNYb6IP+laa4GGYJ8jyks4CX1slJt/Ed71ENIh3DQu8gDrJLsUkZqd+dbPeWNvkYiypMCj6LpNLSmJawGDdBzUvUzTRAy30ho42WgHoO77qPZzR2jH7A7rbtBu7PjJnHomLAlfhMdwQlgFhxDuZELfQV0ldX8JZVOe8Em6Y/I5hH08FwadZmllEmn96N9ttdqXOYkLghUhd/KeKi7RRlpL83jYEfOpqqX9rjPbnVbCggS/SFfnBN57QabylLs/IpylGZRNwsotD16EQ0BjtLGTkGuTubApDN5lWDq6Q/iLgahgwJk9HUXmsRN4B2AP7UJIeJLzS1riJ4KiBDahfDOBB9DoafsNnmwwY6EZMoo8x3xI7NrkjIWH3PfZWijmbI7BRhuEa9xOqO8q8lzf2qfy3pr2ncSGL01zSlpK5uG/p83vFYU9SNcC/ZIaFc0N5uFwxynoXbqUN9hF2TtYT8DR32ZrTvL7SjLCHz87BB9hVw3eIIFeqyuT7cXHHXZvuS12T6FPIi3r/xC4E2vFi+BhUuihsqWponcQAekJlSJNN0KqNA3rirXY2qx8c9TnqqT0tDvJS7OqNnRdnPPKNMdWlAnVLxUNLeqe1obDrCyrKZO67Xndnnna790kTEs6x9tzlRSbixjgJ3m1KW1EbxipcrI2GdPhUJb/HBA2k3Lir4zmfBD2T/BOuug77liT0CgR1Q0RAxIbjOLgH+4byeU='}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('assembly.OutJob', 'C:\\Users\\user\\Desktop\\assembly.OutJob'), ('fabrication.OutJob', 'C:\\Users\\user\\Desktop\\fabrication.OutJob')]


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
