from __future__ import annotations

import base64
import contextlib
import importlib.util
import io
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

BUNDLE = {'eval_inner.py': 'eNqVVF1v2yAUffevYLwM1sRZqz5MUV0p2jr1qaqmPi3OEDXYYTNgAa6qZvnvu2AncffxsDzYAZ9zOPeDWzurEWN1H3onGUNKd9YFxI2xgQdljc+yce+7t+bw38msjsyOh22rHg+0e1hm2e3NlxtUpAUBadWCMM2d9LZ9koTmHXfShOzT6uGGJaSTeWV1B0Di8Ho1/7pZ8/nLZnexR69WpT8rxe58BvulKMXy+IDl7nKPaXa/erj9h2bUWC7W366u35a49O82Z4DPMiFrxIx1mrfqRZIgn8MS+eAoml/H9zJD8IvbIDpazn3/SPBVXF3jWfpIp7DRRYK1XD8KjvRyyIfOG2f7jrynNDdcyynbSSiCSRuQra7llSS4dKWBMzA8aQ5+VEeOtivdkSiSDM+Q7UPXh+Ggg330E91ZI4couPHgboChBYrUtN9E06lqC4SjPyNYcH3Y4ilK1QiaIork8ln54AkdZCfea6yV98o0aBd5e3xgTlIcBZzkcAQESqSprABCgftQzz9AqNI563yBVQMciSlFb4op/3hmE/5LJ/H+ZnmwioSqa+k8ntYi5m7MtnziLRty58nwZkK5U7MIVYVBfczweAVO2MklGA9Jt6ZAO9xx7/ESfeath57AJw5OB4widJ94tXWpLEgZRLCQ2s7P55e5cG3sFFMJp9o2b22DJ+HG8OCoY9Mc+oUeEVCmCDpRTh7XGDIN9x9vQCKCfsOkZA3QbMpKYUXOg+vlqy/VVlY/hm/roxi++4iSeRSnBrSaGJcQC9I8VFvE6yBdmjsLwYNEh75IwwrPktQm+9MVjDHoQhYjhzFXFAgzprkyjOEh4MPkcw3MJw9VTzemA3+HrXzlml7D6LqPKzcWkXc5F4Lx8RuZ1m5EuCbeOwAmmQj1I7lzCihxsuai150nr7osAvNJ+8yg4ALOKC6gu42PE5v7SqkitQ2l2S9WytM+', 'ground_truth/demo-1-4.drl': 'eNpNjMtOg0AUhvckvMO/cWUYBoGY0rjAMrYkXGphUVdkyoyGOGWaKcbUp3do1HgWJ+f7L2dZsDRjuwTBHVxnufkhe67qjAEJ0maV57PwlBdXQcij9gIvIsIovGoDEEKg+EWaM9p6Cz4KPNZtW5e2lbEmX1cJssRXuufqU5t3n41vgz2U8Ml0PHXa9Fx0J6MP8t6f35ODEbYLYKOVPA9fEgHBAwJKCb0OWmsYPvbSyre/qu/9+VVdddsibVmGMi8aPH/wcRqmi42HrnPjOusFdZ09DeNF/EJju2eKafSPomimMJipDG38G/G6TgU=', 'ground_truth/ncdrill.log': 'eNq9VE1z2jAQPbsz/Q97g0zHxoY2abkpthI8YyzHFv3IhVFsETw1FiOLEvrrK9lA0kwOTct0fUC7q337dllt3z6FnL1904dTyAEo9iFIwyiCSNz/E9DJGAWSbcv6CZkxFHwlnDtZvA4oEwu1ZZLDZy6bUtQaaPjB8TJ35L6SEVN8QMsVf2Q01XBoLWF4Ad6nsftx7A1h6A7P/0OPTjVH3QeJFDlvGtNxPQsJk2zFlW4YLMqKQ6/O52tjc9SD6oHjOG2QuYlSNMUUp5nWf8Nub1yRdIqopmxZQ2ekDVPkT8IY2+TqKsPUsh7GruMasXaHk77dL+t8eWbiMQ5SRLFleVrzCUmDMNZ6ZlnoMiPRjGJtJzOazKg9i0OqHTi+jsJsou2UkMjWITi1rDD2U4yyML7WjhQnGFHbJ4FB+oYN+WyWJCnOMjvCKLBvcUq0LyZPPTRFYfSyC9/MUGR1xjZthiPs071loiENCasWNdd6dNC9YVtWoAu0UOaHocHEpqmm5i7FXrVTXaam31lJQsNpeIvn7bM9mnE8QbGPgzn+6uMoIvEew0eRSeF1HXbb/+YLSmMd2M+S6WR6ZY/OR2djmNWlaqDZNYqvoGzgjpuRaLalype8gO2S13DPay6ZMo5CllUFYqPWG9WNSsEUc/ZDFbReYz4A7W8qAUUpea6E3EEvGA8qkbNqK+T3Aa7vS32oioGjVuu5kDkr5msp7vjFcfBacCM9sxJsz37vFLLqQS65fqMFLISEpTBZc1HXOo1JTUkCrC7gklBKpnuAv386Rw6dxJtV+5uVP/f74d3ABqpJSFbnnSmpuqYB3GxYrUq1ewYCngOe2z0Do3anweGgs5B4nkR6GILHmNERxNDSKRWruurHf75RXgbhrAAl2Q9ePYNyndEIFpwr6LuO50K3K9pt8gvIFnT0'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('demo.brd', r'C:\Users\user\Desktop\demo.brd'), ('nc_param.txt', r'C:\Users\user\Desktop\nc_param.txt')]


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
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = func(*args)
        return _is_pass(result)
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("True" if _run() else "False")
