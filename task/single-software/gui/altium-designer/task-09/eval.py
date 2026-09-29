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

BUNDLE = {'eval_inner.py': 'eNrVWv1SI7kR/99PoUyuivEdTGxg2TtyThVrzJ6TXUwwXK4C1Jw8I9taxtLcSOPFObYqD5EnzJOkW9J8GS9wlUqK9R9gS92t7l+3Wq0Pz/PYkiZBuiJTmRFN1e3O3j759z//Rc4y+YFFmmRM0AUj30DDh7NoMtZZHuk8YySlek7yNKaaBa1Wf86iW0W4IDLXaa7DmGeHLUK6bSLYx8AyE3bHlVaEiphw+H8so3zBhD5DUaBHzhSJpNAUxAhJtmQSbxGVT5TOuJiBNPggbyq50ERLoueMvHYqxmQczUGiIn5EFdvhQjGhuOZLRhZUR3Mip1ZkOwBRu3XFKqushofkQqbv2JIlhYrBCU/YKSLBlRm2GFTL1CpmR/8joUlCDsh4zpgerxYTmZBzFsksJpn8qLZIKSdjUwZCIrauvxWn51QTCkqBvJVVi1BFpsC+BjPxP3LAT/FJAigpY91em5xKQ0ysbDTcGbtFwNW136XxWyTNGICmm/LBuyMBOqDVZys9l4IoDW6gYFPCJxnNVghKrlgctDzPa00zuSBhOM1RaBgSvkhlBtoLITXVXArVarm2D0qK4nvGim9qpawQjDEYopCAcdJq/TA4H5Ce+eHDKGBjGLYD0FwmS+a3g5QCoLo1+Ols0L8YHIdn56M/w7fwYvDTBfBtXR0zxWfi5lr8yDIF6vS6Qeda/MAZmBLNV+9lzHrQ0J+Dxiw5l3IBDgNox3qVmJ5zljAIMXUCILKsV5JawVTL7ERmEHNjE7e9r/oS9BegVPiVk8Ya4k2kjVkKCgBvL7wWo5SJkfGA6nWvxRHoBXHs5iSqcMEXDLywSC0VNoEACgKY1UoZKrZIE2h6JyMDPGIG6h6zKc0T3Zdiymd5Zrp6Y5lnEVPX4lKxbHjc69yduE/JAMECKmiWoE61tojGFhYIc5YVU0aNBBoO/kFyNPqUaVXAzCMMbGQ7kx9Zdgb+RRJ1QW/BTi4zrm1vruaD/uhCHpXhc+JEHg81W5yzJUcnvr0EnVEHjJRxnmIoQ0QOskxmaijewy86YwYVC5nBoshyDutr8U7OLH4OqvdUAFvs6NwgQxElecysu4dFOKDoa3F1Vk5sBSGGv9SPCJTjNQ1rSgNXAVoXeOppsQdJKoRkFNjkAKFQwjAQdJKw2MSHbWRjTTP9IybSWiuQDkXM7sDdOpNJwdapseXTKb/r1RoimbLeUZJUTSN0LTIdy3d20l+a3G8cIY+pphPAoGrrJ1Spt0z0+0e5ljVdmx0Y/hs6T02nVeMUps5mZwMhThlmuPpJrnShogXwUvBfcjaMexejs8vT4V+7Dah3N0FtgvGFgN39MsE+G/0Nwd5tgL23CewjQRM5eyFo736ZaB+dHiHaew209zeh/b5/+UKg3vsyoQYAEer9BtSvNkE9HL0QpPe/TKSHIwS686qB9MEmpI/ZJH8pGeTVlwn28Zu3iPZBA+zXm8AeQ3UK1dALgfvgy4R7fHGOcL++FlvVHgUb+xeX54Nyl2I3jb31feh9sX9cKwzvzYbzNF9MYNjXWAcb9to29N4W+IWgdf5q79K7tFXQPfY8bG0oUC+XGip07+2oFyuDGuyGkvtz+vHzzK6YBmABI+KUdd41HOR+NMEa/C9cOLuIM6zhCXKPMtzXqvAm/y0ktlZ5gIlrbtjVKGsaqOw+A5Um90uHBdbEB5hgW8OkqvJooLH3DDRqrC8diuHoARLQ1LCmrAsaOOw/A4eK86XDYFbkB0jY1oZJ9aW7gcerZ+DRYH7pkLh18wEoRXvDsuYi2wDm4BnArLH/76Gpr2L9H45H/XA8/PtgDGvYr1tNULYOSffbvc5+p7NNttYXAOg8ONjtdA9cXyMNIudB9/V3u66zygoPZJYTBXs6nb1XBU89YrBv99tOydQErVTlU6t/8iZ8f/R22AdzJivNVIDnknN2528dd/on3e6gc9R90+0eDbpb7Var9XuyU36I5mJFhqdDktJMsYz4/fN3JztaJlAoCN2ukbZaMZuS0NCFXHBfszt9SJTOgOpPJOaRvoIf2yThSl/pPE2Y/Q1/bm5uDs2RsQIv4uHq4ZP06JtPhifKMzwsNUORe4LlDXTiP9ONlwIZ/YjnwahRoNKE64QLpvy2HRQ/2ABcQBjgSX3qt8suPiVQshmKit4MDAUgFzmrUyIVSICyUeGJtu9deW1z3m86mIhd843XXhNmrQAdkPKqe7jTvWkQFNAEiunYnlv6jmmbXN20n1StGIErA87Ttng9z1gOyD3D+NttEm6TpTMAT7A1R4V9EFMpV1hx5bS5CWiaAiy+f1sAD0LaliFjOs9EydNqhJgqjvzXAs2EC0aPCynP886QgfzsEmAQBPe3bNVbQuaB7z+bSw0wUkvDi1csyK4CvAewaiAfxGQlGqy8uvl/hxdCqgp8zTi+d1/D9nZZTYpCtRQVM4xN4U33ps3OjaM3fZx+zsFWkavSmwjVsm7s7bI5mEO3iIPbZcP3rrdw/ZyqUCaxryp/T6RMDussHhB4aJUKEkzOfttx4zVhaO+ElF/dDZXpyUqpXUq5C5oaaXVF40Y0dzqAupfClsk7JCc0UWwbdCh5PKNqXcinlmHGpJ1mH4C7NuQfiFdd6XklXRnsj1CXd2CWzcWVGyXgylwz+W28OSs6SrFVd+Uca9yVlzGqpPDQkbXRjJgNl4+QXRZcKS5mXk2S8yUKLJTzm3ZUd3leO7A3mFbXz9JV9lYMj2tPBQF2kroLExBe4YrWC3unuaBcqM9pb5p1tqpGshecoZMaYhaAwQrcYfzYtPlMRDLGuzQv19Odb71twszFTs/DqRLp2iRyIkvt6kIrn/1m0ewuYqkmA/MPZi5exkLb46BF5s6T4GAlcjbjeuQbE9ogov0YWrxRFmyAq01+16uTbLz2fH5kRnMqZiwGl7IkVkTqORQuGhrdpfcvOc+gu3Fzb++v1RMx+2Dp2eioujkV6WfOSZ5tVjXFnmlf+ny70ME0SfwH1YtbMl0NA6tNUQysrxe41phFDvo3gtJYGGuVklkkngBhHQABK7UECDK8sFck5SnbUe7mOK4/VXh0ErO7FAKQxaFBCMaBwsrfuA+w0e3MKqh/RXwDkzLMQotoN98czBI58dGD4deuKvfanwrIG9IgXpraPI5H87FFlbrAAEy+5qXIo6ajwsixTfCQET0RKv4P47yNAAQcNk6N9GrMXVuLUGJJ0EiR+Impplg4IGomc5m9SK0QejI7PSdDYU5yj328z2SozbOgNhNQ0/osKDdQ7Sd1KYbGZdBMKmgxr3dG7wbEPKHIYR7hZtc5z3ueWuBgH9Vqk+/Jfue7g2IR9zvBK/L1mhe/79Xpe6T7kOY3WAIlF0x+fL6S0Bwf6LDCptglUIISHzOkVR/DFEo4wkXmqsuiJzLvr0zfVSnNK9acYhdgH/hkS4h/82ZIFu96FFsysTmrb1fi8GlTteq78tJkNyHFDjh9BpPIZdZypLoAdgdTF4a0wxVT8Qk3wwj43Mw+TXLSblobkGq1cJkxSSAMSQ+iOwyxHglDz7qseIiUzcwCYzNTCpAVLcFRNnMI4I7dTTCaBjSOQ+r6/HqB6iiyGaY1aip7WLnwd1HmQnujeMa+oFbRGqo0gz2Uj6+hgjhfpMqHvToXMR4s7UJBIhQuBVRFnPdMlew2eWqlsHzTfgcDHbImZGEbJG3CgIx0263/ACFsuaU='}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('old.PrjPcb', 'C:\\Users\\user\\Desktop\\old.PrjPcb'), ('old.PrjPcbStructure', 'C:\\Users\\user\\Desktop\\old.PrjPcbStructure'), ('old_Analog.SchDoc', 'C:\\Users\\user\\Desktop\\old_Analog.SchDoc'), ('old_Debug.SchDoc', 'C:\\Users\\user\\Desktop\\old_Debug.SchDoc'), ('old_IO.SchDoc', 'C:\\Users\\user\\Desktop\\old_IO.SchDoc'), ('old_MCU.SchDoc', 'C:\\Users\\user\\Desktop\\old_MCU.SchDoc'), ('old_Power.SchDoc', 'C:\\Users\\user\\Desktop\\old_Power.SchDoc'), ('old_Storage.SchDoc', 'C:\\Users\\user\\Desktop\\old_Storage.SchDoc'), ('old_Top.SchDoc', 'C:\\Users\\user\\Desktop\\old_Top.SchDoc')]


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


def _materialize_output_view(root: Path) -> Path:
    stage = root / "_output_view"
    stage.mkdir(parents=True, exist_ok=True)
    init_names = {Path(rel).name for rel, _ in INIT_MAP}
    if DESKTOP.exists():
        for item in DESKTOP.iterdir():
            if item.name in {"eval.py", "_runtime"} or item.name in init_names:
                continue
            dst = stage / item.name
            if item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)
            elif item.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dst)
    return stage


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


def _resolve_arg(spec: str, output_view: Path):
    if spec == "__DESKTOP_DIR__":
        return str(output_view)
    desktop_prefix = str(DESKTOP)
    if spec.startswith(desktop_prefix):
        rel = spec[len(desktop_prefix):].lstrip("\\/")
        return str(output_view / Path(rel)) if rel else str(output_view)
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
        output_view = _materialize_output_view(root)
        module = _load_module(root)
        func = getattr(module, CALL_FUNC)
        args = [_resolve_arg(arg, output_view) for arg in CALL_ARGS]
        result = func(*args)
        return _is_pass(result)
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("True" if _run() else "False")
