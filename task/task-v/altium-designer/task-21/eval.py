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

BUNDLE = {'_shared/build_native_task.py': 'eNqVU0tPhDAQvpPwHyacIOKaeDKb4M09Gg/e1DSVDmxdaMl0quu/t+W1ajysPRCmfI/5pqUh24MQjWdPKATofrDEII2xLFlb49IkTebdN2fNWri9Z92lSRMVBsn7Tr8u9IdQRl6aKGyA0CELlu4glCaXL2/bEVfA5S2wHzp8imU5br5s0wTC0kZzhEIFCwuuIBu3G91hNsHav0AtWW+UYPK8n3G6WRU3eNSOXV7MTnFNkTbUMyHmC7JYue2ZzPYHbzHsD+GZD5LQsKseyWMJo5Swh7Esvoc5G04Yjs6sNuXMP42/tsOnMOEw33GcWe6spxqn6Zeg0PG3k7i3Brdr4nALYIL/lZqkdgi7oHlveRenfUdkaTaY+4v6mynG2ZnmccbOr2e1qdHiFOuDNKPA44A1oxLxbubxGq65JMstKF3z71wR9d+ORs5kyXjk/DSEaLxRvh9cHi3LcBIqiFXXQci4+FdJV2td7WTnsIALyJ5NVp74aGqrtGmrzHNzebN8Cr5fqAUoRg==', '_shared/native_altium.py': 'eNrVWFtv2zYUfg+Q/6DxSUpcI277sAXQCjdxi2CpUzjpsM32BFqiHC0yJVBU4iDOf985JCVRshOvGPYwA4FNniu/c+FhYpGtnCCIS1kKFgROssozIR3KeSapTDJeHB4cHpjdv4qM1wvBDg9ilM6pvE2TRSX6FZaGIh/zhC8rwoVkgi5ShgqvLkfBl+HnizPHdxZktj4/ma3PPs3Wg8FsPYLfQ/j+CH+DIawHBEUODyIWO4wX6CgH3+5ZkKXMRfOnyqrnvPnZGWecnR4eOPCJqKSgHxn6gtEoWDxKVriepiaxA2dUTP1CUiGLh0TeurVnntGCH0GTgjm/0rRkIyEy4cbkSanldMWenaRQqih3hqlMypUDSpwwg2OXPHKiLCxXjEviNcdQ7qRwCD7oHqCQwlgWDILCt/3vRyzMIuYSrYD0HIZOFT5JljwTzDaUU1GwIE9yFsQJS6PCLdgSvTlFQ8pglIRyCose7syN7awEjjYFoHx61tQ4E6hZOgl3jL5+kaeJdMmG2MAByMQnCp2EKxGLiJ8w43CGkjW7dz3nXkVN1Dp9OOLAa1jAuekd+nPfAgq2rURZS0FDGRThbaBCwcHJogt2mhRyiseszr07v4xtCUrBajd4hrpIs/CuUPR+nPAogXx3rRwis81kdHY1OfcHs03/6IP7wbd3NvXi3U+4+sMjvUYaTVvLOKXLwgdD12bT+NCc9NQ6G/g0nTeRW1EZ3mI8tMdWRNQGcCuO/lJkZe6eWMDrFNLR6aSVErVYI1ZANlIJ9nxVlA3pHutoaxdcxzza2le5Jlborw2sBed7jedscwMg+e70z838yJttxlCbenUMK0gh7WInARHYQHnUc7Ca8XBiZc4+8HrW6q3XFsUOoiR8h6jeQDq67cM2dto8LLXVnGkQdilq8NmlCuAOVjr3CkZFeGsD9O79FkDHFUDndZwsjFoFrFR3HGpFVzHUiLUiqpMRO0dbnsCFIVhMTk1K9ZcM6vwyWUxYzATjITSxXkeksQlizaLLdq8joYHvEsMK3wrOLsMaSIHMgoRLt+VaFqrrsP8b8bY8e9wn9PsOISghwB9SuQDpp+cuWdCHQAUDqOrbYnj+P1RHHf2pfdT5FNXMX8jipn31aZ4zHrn1jtdq9Q1j0/Gx0y8egyYzus2+uc7sjt+56aqGaV91aA0RfuVOsYFrFQfy6Wyw8nerwAyhgz7ecw1xbrTtv/PycBEoeM3dvPvas277f3HrGT+mYEphhd8AFQpV1/dsfXJCPDULbIgZGea7vRZlyl6+pJtZpHJc8Z/u5Ohcesav1yHqji6Tb5ejXy7G580IA+x7JxjlVJXAOwcwrw2eEtgNyD8YXbZRQaH/EJXrq2+Ts9H56Pri83h4czVpoeOAVvJ1eHMzmoy/Dzbl9ffApgR2w7bIqIgqyRfbgFUBrye5VrRnIK7Hqhca8Uf0abZRPRcasmfPf4ampz497Fkznh0Ac7+UOTxc2A6YsMSOWwPcwOvgpjkb4NBZEBeFVPVn4dVzjnoqO++ARb0Y9DWgfjobNamZgW0HtIbBKlVUE6TZA8POWG301Ub1LEP1NQsuKnI9brEU3mLNjIjQo6puHjetpJO/SNAduSpvgJwQrzb0g99xdm/qGteM3+Y5qMCh8ABsDI6HX0bbxhrR/a2laRitkGo4WgGlabrVTrfjua+VIOOLsap6v9BBeCUCCvdXQYfpFw1Y9wIMVPgPh5b7+FrXZdh97KtX8oOAolMdzEXRflRCh3BRqAfORdDR/Le96rajRZgk/icK6eRByZAZx5c0h6d1wpc+KWX85kf7KV1NeGpmsStAuQKUdr7DifXsD+lgbW8FTXUf8bhNrm0ZtNk6ZLm0/gvxksa/AR3nVXA=', 'eval_inner.py': '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', 'ground_truth/expected.json': 'eNqtjkELgkAQhe9B/0H2YoGHVfJQ4EHTg1AiWiFkLIuuINS66Hqq/nuzacdAotMw89775t3nM01DVdNI0dZckl6UVLIObbS7UkBL1rCgJEi3JsZ2tsKZZUc7bB+wjYyPx8TfTcrzfDtRWVeVoHXbka5oBFOZkPtwZC3jsqbXGMSFfkw9i/j6cuAjziTh9MaIoFKylqt25+HzWBJMo6aQef6I3H3gDBgSwX4K09DbBc4hOQaf1hAqmp5LiJjD5WlMp8b/pcauaRFAT+uLfyPH08lqXOYzmC/iLYi0'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('wifi_board.PcbDoc', 'C:\\Users\\user\\Desktop\\wifi_board.PcbDoc')]


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
