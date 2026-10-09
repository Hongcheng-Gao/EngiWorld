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

BUNDLE = {'_shared/build_native_task.py': 'eNqVU0tPhDAQvpPwHyacIOKaeDKb4M09Gg/e1DSVDmxdaMl0quu/t+W1ajysPRCmfI/5pqUh24MQjWdPKATofrDEII2xLFlb49IkTebdN2fNWri9Z92lSRMVBsn7Tr8u9IdQRl6aKGyA0CELlu4glCaXL2/bEVfA5S2wHzp8imU5br5s0wTC0kZzhEIFCwuuIBu3G91hNsHav0AtWW+UYPK8n3G6WRU3eNSOXV7MTnFNkTbUMyHmC7JYue2ZzPYHbzHsD+GZD5LQsKseyWMJo5Swh7Esvoc5G04Yjs6sNuXMP42/tsOnMOEw33GcWe6spxqn6Zeg0PG3k7i3Brdr4nALYIL/lZqkdgi7oHlveRenfUdkaTaY+4v6mynG2ZnmccbOr2e1qdHiFOuDNKPA44A1oxLxbubxGq65JMstKF3z71wR9d+ORs5kyXjk/DSEaLxRvh9cHi3LcBIqiFXXQci4+FdJV2td7WTnsIALyJ5NVp74aGqrtGmrzHNzebN8Cr5fqAUoRg==', '_shared/native_altium.py': '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', 'eval_inner.py': 'eJy1V0uP2zYQvutXMOpFArxqGvRQGHCBAt2ipyJog14WC4IrjWQ2EqmQ1GYXhv97ZyhSD9vx5tH6YJsUv3l88xJrozvGeT24wQDnTHa9No4JpbQTTmplkyTs/WO1iv/ts01qgvbC7Vv5EHFvcZkkv9/+ect2fpGhbNmi5LwwYHX7CFle9MKAcgkKKQhfSGXBuOz1hllnMkKHI+x7lnK7x/9VmufJqFKhXY/ARevk0EXFttzzh2degZUNHtCGse+Y0h/Elt3++PpNkiQV1AweRcv14PrB2Wz85ZU0Obv5mVWydNuE4Wd+EJ1YHJ3d8GeFspx8wJMLGJqtbSnblizhTrdghCqh+Kvc/6rL1CMbF4GeLoQ0Rg+q4s4Mbp/SBjz1UDqoCqJ+RBnw7u7YIe2FtemW/SZaCxtUOKnHTeJxYfQx8WBZIyVusrmAJ2mRiHx0exZ/lxoQpPIeFdWTGcFDRgFlnbRWqmbLDlHcMV2IwXRSQdqo25nnWc0kceezqmi1qGwWGEGGBbIATy4DVeoKtezSwdU3P1EORBGl7nqL+LPAZ9Ge8Sw8ldA7dut/MJ+ZsLT3gsuDEg/opNMMc5Nsjb6jOugwAUt0HMVc99nAh0Ea72b0+C6dsmFtdnrvIbU2D7KqQK0w0+4CYAOix4QE8wgrQNzkmPDDuabziDwIC61UcJHRmKBSSefLOT3J8FKbKbn/W9onuz6X+JDnFlzmUyRnr3Z+FSVdz/aUQFpR71n0EsSzci9Ug7EcVKS5fb5mBMZsIWLDtJGNVKJF1yavCumgWxVgORjf+HZjgt/NEu6nMyS5ltBWJCpLsf0aqFNsAT7Y9AexHUpJF4IDL0F+0SAjXobnJ9q22F4jPxmxw2zgsTh46PEFqj5NGX2iKVjCRnRU4YcV8j08b5l31POAy01YIhkRjAVAaHBAZRJZPuUCsUWJkah1W2Weh7k4Z3OPp7H5KssC9v8xbI5rtG0R07C1jueLsWR+NmDrZbPBnxHXC00wDApqLLgHVUbFGDsjTt5FqeaxeuNwud4touRFT/RJcN6pw8nr3fq0YKfYxWZ6Xq2NnirVl84Sfjjmfi9UZb6MFuEwRP7Ji4HJzirnpOz+9oZeCs7Wazrg1ytz3LCPAjvLwWvF9Tpy+UtxPKXHC5NqGnJX2Vn2sZMa8By9m9L7Ek+k6ttpmnRQemFmlPuL9ND3t7JDvEwz+wvTZUHOYvcKQfRKR4PgDxxb2PtPm/5XUMW6wY5yDZSAL9tMsJm9ycDNkr4v5Cta5V9iyaZ3ZoDVEyzf8v347G4efTMR7KORzoEnmh1Cb5n6yjHdLEBKqxsnDDJJ1jvLWqgd+yjdHpvF7Np2kjMFbyUoFW07z/HQ6mnk2alHVOH4fXLB8QQjxrlC9vCmtcOuznknpOI8HUMWL1+mQSstjEyJHhmIW8UvphlotL+llYmXkL4QVcVFeJYt7wLhhGloYOFBL4aOxrmDhg8t5eXqckQHisUNIrxqSpTu39irAZM4G7EbTD+kyu3ebBgoSxdJge+GcuevJqGr02UPZwre8ihvR2BMeEyBnAGeZT/kyb+jp5cl', 'ground_truth/expected.json': 'eNqr5uVSUFAqyc9JLUrMS06NT6qMT0ktzkzPSyzJL1KyUqgGyQNVBBmbAHlKpqpKOnARS3QREyOQiCGyGmOoGpBALVhYKS2/KCkzJSU1D8mmYqCyaKimMCMTuAHOhnBmoKEZQtgYzvQxBJsdCzG7oCi1OLWoLDW+LDGnFI9vIC4NSoUbA7IUKBKWnIzu+KBsdC8HZSCJgLUF5SC7GCjgbIDsVpBAcmpaErKjgWI+BpBg4eUCIgA5B1FG'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('oscillator_core.SchDoc', 'C:\\Users\\user\\Desktop\\oscillator_core.SchDoc')]


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
