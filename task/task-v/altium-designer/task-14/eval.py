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

BUNDLE = {'eval_inner.py': 'eNqVV+9u2zYQ/66nuHH7IKGKWmcdMBjQgC1LNxRdG3QdsMHzBEaiHdYSpZFUYiMzsIfYE+5JdkdRluS0cZcPdkjen98df3c8M8bELS+TZgerWoPlZnP2/Bn8+/c/8PLVxdXFd3Al880ZV8XZVclzAW9a+7K+BtOIPAmCixuRbwxIBXVrm9ZmhdRP35d5k18nXnLxxp38oOu2mS3nAcAsgsstz225g1o5i3j+bteIlHxB5+dO2htQbSW0zMG0q5XcwgzC1+ksStDGeQQXddlWyswAUvheGLlW3NY6vqirSigbv+I7oeNf49/it7XlVtYK1b6M4BclLSmRWiVL3HweoX4uK14613iYwjnuf0X7paykFZr24iB4oxC0vRFwtbM3tQJjMTNcF1DKa831DqSB1ogiCRhjwUrXFWTZqrWtFlkGsmpqbYEr5RGZIPB77w3i8/9r0f9ndqYz0nB7gy56C1e4DIIfL99eIixahOhFlugjSrQwdXkrwihpuMZEBEFQiBVkuDIik0qGVmztHKHrCM6+gULmdoGLGGMwdmHbphTdGj+WS3djAEbkDvD8pDwiut87nbzVBMC5gr/gNV126r7cMfFN8zsiDyFKTFNKW0olTBh1TumPNlALBRM0I5swOhzJFWAincQg7xzXykrVirEkSaEFrq0haoVswSK8iaI7EKrw20sWHRnrokAMJLmYzc9my4lAn5rECIuZ5m1pQ68Uw2IZnYTWe0DuuBxhXljKXGyYm08IbxNDFsOth0j3biVBCtHM4L7HufD+lglvGgw8DDd9atFI1ClogZxVBx1PImoVWVfpJhwq/sCjDudw0LNzJDrw0/txhEbOsIYbw+bwgpdGxMAGHeYYNDayD5wyVyajykD1kc+nwCYdiAUjsvQqidgieydM66AsmBYci5ERkVdMbLHRWVF4B0BVhm3DGKnWc7jvze3ZyIzLXGetw2n1bnBDXEfTByDorshoMxQqrwu0m7LWrs6+ZjEIrWttUoTUUGfylym2uWgs9lD6wtsBbkCciCN3TQfIGUyyg0GIx9EjBwzaOGogUZ9VNu7vB9aS0qOQmE/i0fvQM+5jiGhnTaJoghgXkqPFFAOWnJP7HF5ILHBeljB6WDx9IRzendejh6eLq8F1JostBb6QyoZV4ryGs2haz9B3sg0VIAbuxBJ8MioTfkS0IrmFFknFbX4TavbHACX8vXgSfYFXv4mWD7Ux3ZVrWrd9xSZlfSd0GJHJkBFs6KiCFUQrz5tlf1ulUOEhuAg+S2H26DWFoxIQ/tGePUxnDGu8d/YQ8Th0dj/1vh81p4e3rND7QXbxbBn4fvFnKzWCwY4RDJb9LHCv9tgs2CdNAywe6buhwGvjUDA5m8wGXub8SMJPCf409qe+TXl63HHlSqMPoSfJkH/KYeoZtBY23EzeOjr1T8T0PfhgwffldUjYRuyw1jd7dqR7nPfBW88xYgmB79cnvSNp0NHcIb7Hj8/03od/T5+4ZNEjKHzxXip+XSLwJ4AJIf7Z2s+KP4lCthVOgy/qshAafra6zWnGOjSlIYcr3xu8NbohLA0WjYNjM3aifR7bgKo1Fq4FzB5rVCeAZJNojmD5PhpO8sSc1Dvduvq29B39T+RTp6fjCMaW3RNNdgnC5CR3PwTc2WJUGQ8aBXAKqxBbcDdxEO0r+FNn+bGqK94UyzaezvHpeTwM8Gk8VumSAMJTjFrqQLJjVkHlkuX1l8EHkhTgVWeZ4hWN+SkyKssqLlWWeWL1k79eu1e0m17oDet3km/1uqVYr2il/dPBm4QXRcb9WTgeiryEXlPOULB7nmndj1a4PxnY6CwZTVHdS6fpeaOfH0nRVo0JcZCnC1KW0ieUoZ8u3ORSpm4y8+8f/jKhEcqGz4jl2jG8o0cEAsXwR17wH+6NZxY='}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('spec.txt', 'C:\\Users\\user\\Desktop\\spec.txt'), ('template.OutJob', 'C:\\Users\\user\\Desktop\\template.OutJob')]


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
