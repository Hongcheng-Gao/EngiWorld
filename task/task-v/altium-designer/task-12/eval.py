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

BUNDLE = {'eval_inner.py': 'eNqlV/1u2zYQ/19PceWGjUJsZU4RoPDgAkWafgxrarTBMMDzBEY6O6xlSiWpfMAzsIfYE+5JdqQkS7ZTJ8D0R2KS933H3x0ZY3gjsqi4h1muwQqz6D9/Af/+/Q98QD1HsLc5fCztL/kVzGSGJgqCs2tMFgakgry0RWnjVOpjjRkKg1FFOwwABiFMPnoC2nhDvFO4RpGiBoOJlbkCvJPGGshVghExnIRwlisrpDJ0JBKb3cNpI+OtzsviYtrwGlDl8go1ppAQj1RlXhqiH0TRqZP1PITLa4QLsUQ4gktBrthK0AdMZbmkzd+ElkJZT2K1LDKEfAYokmvoqiRh9OHXUmQGLMlMcq3RFLlKpZo3nDOdL/0p3hVkIZm1dOFLyd6vJZKDlRgujMHlVXb/o4ETmDsFhuKqje05bgUzcaVlIpyLRPK8Jgkp6h8Vuec0jO/tNQXPWKFSoVPI5JUW+h6kgdJgGgWMscDbE8ez0pYa4xjkssi1BaFUbr10EwT13heTq+a3xuaXuTeVkELYa1LRSBjTMgjenX86h5FfcNJCyY3jMKKw5NkN8jAqhEZlgyA4/318fnZ5/jq+/PR+/Ov5Z2Ka+FBw9qoOBbzW4pZCaVgP2Js8cxXy2eoycaa7vc82ZWGv5hrLZAE/wDgTiTv03+Ncb1FTsTT0B7g+zOYt18UZ2SazrMv3ONf78Vn/5PTF4KlcUwpTijOIKWgGY6kkt3hnh5RhHUL/JaQysRNa9CjVxk5sSQVXrenPdDodesXNxRg+Sk85WK09T1JqlyevCv6Ci1whHbp//tghAuXG3XRnUWSKTNpMKjQ8rJS6z20QFxFGxt0GHm6O5Ayo3jxFS+8VV3cWu5SOiiQIbc2tpLpiExZSwabVAaq03p6ycEdY5QXZ4Cgng2F/MN0iaEITGbQUaVFmltdMPZhMw0dNazTQFfMxoriwEfO+UWye4N6iB3EPbmoT3fWw0pnESUyrvrFzUuubRqIoyHHOF01oSUhYMWikOlIbnrqIHJjHFSwb3sLzpo4qO9uD5hJ3SNtrXOvx955qhhWEXmwIbwgJkeq35WG+grpC1oFnFsrEDkCIvaPzGNh2u2BBp1oanqhqD91Sq2yZELcg0GKukmdsg7iVBt+mYCmNIUwZwqoRt2YdMT50lbTKUKvvWzWu2En0xhBSl8ZukxOS5w72R6y0s/4LusWoda7NiEwqPCRVQcO7BAsL5/6fa3WCWtojfiQenMEpg51uCis8bD5VgSEhOxASNmFlW314U7iO66BRrA7jI438oGlzXcTaAwRGSb4siJ9r9menxfI/0qPw+zpyjpxau/PGkAxMuVSWV0KipbDJNV+EkW+LfBBuX932c8i1aFx0EdgRsInMRt2zkUdLroWaIx8QdqLiu90rpLGBlB6MGd8yqVOezUjT8Zymlc5q9aDKNbAdie3A04M5ZXLVONGpkfBQSr6DMeq+j+GTJySea8p436AyhFw32KslUXkkSNKrcczVyrI0FgoCEdQ3DiqJLYw8NVWTTwC67E6mmx4je8BvSVGsSFMP/E/rDaoXN4IQjLLptKAWFvfC1PtGITzt811nNOgkdnHjbHSIyV0JTWasmyi5Zp2uQTnwlhMDsUVkNo0OtGbbJJVHXaL9oO+wkN9d+k4+2FaT3VhAVbwJ5HZLamPfNJVdlyInd1hXVC3wmV57gbDaiKWtfeW1b436avmYAXsp27NoP0Ad+yolOxZuNrcvzZ7BLrKNtfT7/5vayU3HRhK9Y2C185B1ZFmr+DAs/wws+pJLxVuGyfB0uuWlA5P2OISXcLrt5Z7gI9eFgB+tdln7cLqGZa4xPIj0jUA/Jjg7L3U9AjUniX85+rPJRhLbbS4eO5Rl7Z2esW9hY/el1r4NGzgi1CWI/RZv9+HYUcb8E9CD3vFDuHi8hYsNoDUwXwuaBg8EKaC0xP4S0YtsRHmM4yW9duOYVZlpHml67vt4NUEVbhKpd6JXek4IqOzYrXQ9oYkiEmkai/qMdwezmkLPHZwRYTUguHUz3tH+1tDozqLOJOepCu26sHspRmm5LAynx4RUKWkbndAMpIx7ZQqTSDny02HdYOkR6aY4y39yFakrFPPlEQISGTXT4D8fihaL'}
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
