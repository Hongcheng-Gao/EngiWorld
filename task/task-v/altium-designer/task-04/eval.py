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

BUNDLE = {'_shared/build_native_task.py': 'eNqVU0tPhDAQvpPwHyacIOKaeDKb4M09Gg/e1DSVDmxdaMl0quu/t+W1ajysPRCmfI/5pqUh24MQjWdPKATofrDEII2xLFlb49IkTebdN2fNWri9Z92lSRMVBsn7Tr8u9IdQRl6aKGyA0CELlu4glCaXL2/bEVfA5S2wHzp8imU5br5s0wTC0kZzhEIFCwuuIBu3G91hNsHav0AtWW+UYPK8n3G6WRU3eNSOXV7MTnFNkTbUMyHmC7JYue2ZzPYHbzHsD+GZD5LQsKseyWMJo5Swh7Esvoc5G04Yjs6sNuXMP42/tsOnMOEw33GcWe6spxqn6Zeg0PG3k7i3Brdr4nALYIL/lZqkdgi7oHlveRenfUdkaTaY+4v6mynG2ZnmccbOr2e1qdHiFOuDNKPA44A1oxLxbubxGq65JMstKF3z71wR9d+ORs5kyXjk/DSEaLxRvh9cHi3LcBIqiFXXQci4+FdJV2td7WTnsIALyJ5NVp74aGqrtGmrzHNzebN8Cr5fqAUoRg==', '_shared/native_altium.py': 'eNrVWFtv2zYUfg+Q/6DxSUpcI277sAXQCjdxi2CpUzjpsM32BFqiHC0yJVBU4iDOf985JCVRshOvGPYwA4FNniu/c+FhYpGtnCCIS1kKFgROssozIR3KeSapTDJeHB4cHpjdv4qM1wvBDg9ilM6pvE2TRSX6FZaGIh/zhC8rwoVkgi5ShgqvLkfBl+HnizPHdxZktj4/ma3PPs3Wg8FsPYLfQ/j+CH+DIawHBEUODyIWO4wX6CgH3+5ZkKXMRfOnyqrnvPnZGWecnR4eOPCJqKSgHxn6gtEoWDxKVriepiaxA2dUTP1CUiGLh0TeurVnntGCH0GTgjm/0rRkIyEy4cbkSanldMWenaRQqih3hqlMypUDSpwwg2OXPHKiLCxXjEviNcdQ7qRwCD7oHqCQwlgWDILCt/3vRyzMIuYSrYD0HIZOFT5JljwTzDaUU1GwIE9yFsQJS6PCLdgSvTlFQ8pglIRyCose7syN7awEjjYFoHx61tQ4E6hZOgl3jL5+kaeJdMmG2MAByMQnCp2EKxGLiJ8w43CGkjW7dz3nXkVN1Dp9OOLAa1jAuekd+nPfAgq2rURZS0FDGRThbaBCwcHJogt2mhRyiseszr07v4xtCUrBajd4hrpIs/CuUPR+nPAogXx3rRwis81kdHY1OfcHs03/6IP7wbd3NvXi3U+4+sMjvUYaTVvLOKXLwgdD12bT+NCc9NQ6G/g0nTeRW1EZ3mI8tMdWRNQGcCuO/lJkZe6eWMDrFNLR6aSVErVYI1ZANlIJ9nxVlA3pHutoaxdcxzza2le5Jlborw2sBed7jedscwMg+e70z838yJttxlCbenUMK0gh7WInARHYQHnUc7Ca8XBiZc4+8HrW6q3XFsUOoiR8h6jeQDq67cM2dto8LLXVnGkQdilq8NmlCuAOVjr3CkZFeGsD9O79FkDHFUDndZwsjFoFrFR3HGpFVzHUiLUiqpMRO0dbnsCFIVhMTk1K9ZcM6vwyWUxYzATjITSxXkeksQlizaLLdq8joYHvEsMK3wrOLsMaSIHMgoRLt+VaFqrrsP8b8bY8e9wn9PsOISghwB9SuQDpp+cuWdCHQAUDqOrbYnj+P1RHHf2pfdT5FNXMX8jipn31aZ4zHrn1jtdq9Q1j0/Gx0y8egyYzus2+uc7sjt+56aqGaV91aA0RfuVOsYFrFQfy6Wyw8nerwAyhgz7ecw1xbrTtv/PycBEoeM3dvPvas277f3HrGT+mYEphhd8AFQpV1/dsfXJCPDULbIgZGea7vRZlyl6+pJtZpHJc8Z/u5Ohcesav1yHqji6Tb5ejXy7G580IA+x7JxjlVJXAOwcwrw2eEtgNyD8YXbZRQaH/EJXrq2+Ts9H56Pri83h4czVpoeOAVvJ1eHMzmoy/Dzbl9ffApgR2w7bIqIgqyRfbgFUBrye5VrRnIK7Hqhca8Uf0abZRPRcasmfPf4ampz497Fkznh0Ac7+UOTxc2A6YsMSOWwPcwOvgpjkb4NBZEBeFVPVn4dVzjnoqO++ARb0Y9DWgfjobNamZgW0HtIbBKlVUE6TZA8POWG301Ub1LEP1NQsuKnI9brEU3mLNjIjQo6puHjetpJO/SNAduSpvgJwQrzb0g99xdm/qGteM3+Y5qMCh8ABsDI6HX0bbxhrR/a2laRitkGo4WgGlabrVTrfjua+VIOOLsap6v9BBeCUCCvdXQYfpFw1Y9wIMVPgPh5b7+FrXZdh97KtX8oOAolMdzEXRflRCh3BRqAfORdDR/Le96rajRZgk/icK6eRByZAZx5c0h6d1wpc+KWX85kf7KV1NeGpmsStAuQKUdr7DifXsD+lgbW8FTXUf8bhNrm0ZtNk6ZLm0/gvxksa/AR3nVXA=', 'eval_inner.py': 'eNqNVltv2zYUftevYLUXqXW0tN1DYUwtulnDBjRLkKTAWicjGImyuUmUSlJpAif/feeQoiQnjjM/yCTP/TsXslRNTSgtO9MpTikRddsoQ5iUjWFGNFIHQX/2j26kXyvuV/pWByUqaZlZV+LKaziBbRD8np1mJLWbCKyICmzEieK6qa55FCctU1yaAJQkKJ8Iqbky0eGMaKMilO5ZyI8kpHoN6yKM48CZlODhNaesMqKrvWEuNYbS05qKz8BbVtAKDuRrQn4gsvnG5iT76fBNEAQFLwmtm4JXtGZtZPiNmaPxmBy8J4XIzRI2s8kKPpeX84DAD1w2XEkIMLJ7/KkwO/olW6Tnp5+zi7uj40X26ez48+mvWbr8++7y5cXdHwu/Oj0+/yuNPpz8jIv3ePgqtqdf/OmX/jScqLccXz3H10Fu4c4W40ny8sPF3Z8fjzJLwAWQLm4OD0eVsf02HcT8ZKwQ3ube8pWNIjUz+ZoICaAmpZCFAASiHogZQfhmpKzYSqfAcBbPB88LZhiosvLJSjVdi3aieGCQrObAgHxJ27RRiB6HIx28XCLPZc9kCYpD4Uqk9bnk16yisG07oyP3TwsxpnPuI+4JvjonrGN9Wl4mNcXiBM6JGNRj3kjJc9MoCnVP3xbJSX71SVw5ZIUUxovZLgABe4ZNED4S35JdPZJEvGRBjerM2grzmxZkeZFgV4Y9FLb+IVthy7QO5+Q3Vmko/3B0O7S1PQ32PnDultAWZog14TdCA4CT/Dn1yxCaCU1iFsrBjR4ZgsGRWmgt5GpONl7d/aSAXcKcNmfbqNvRzKAxtQMnqRpW6KhHJLGdjEUWcZk3BVhJw86UB+9wKAwqHk6AyPuxj2dI2Mhkj+xs0ODOZEpMBspEbhR8Tmbwx4nwm5y3hmT2D2YuYRrPnsG+k+wK0DYN+KkRNJ8EKCfFAFOyASX7oYe0a24i529MXqR2O4l7fwGEbxcuViDmjSpQmuRrJleQwE76XFa3QK8s1M5d3wb7XPPCYwKGml+Bj6FD1ijAEuZSrcOYwHja5nmgox8mfa0/IO4PdKvffIUTwxTYIQMKE2/2hYZzFCfZzEEBE6vjGmfqBPgEBmu91YB5h8PKUd0gHAu1dNMTwwI1T0bW86ImSPXE+DbLkyUnG3nwMOZd6YbSQ38mtbcbjSkFxiH0RseHQ0SpFLwqZuQ7k7sCcyg8RmoM05aBVWKLG/X8z1BdAMnGCt9jxu3NNScrwHizrfqFuu993OAXts8FHkzt2mmNVs9VH76n5Gue/+toy0FjaL43vvLOzrMTP22gBTl0WEHMmsPmWycUDmYl4Plkn3IErlxmuA5noy5WVWRXVsdKBlU1w9osQI/IWbXdwk7XZbAjxgByQCniCA/LFJqIUtREaehy4N+aagVvPM0dKKyFYP1R8lGtuhrsnuBO+Qu5TVhRUNbToun91nOoFQ4MYLRqkFX3wnC3dxXeklsPBWRIJreie94pAdrtLVR0dasjJ4tdi1ikb2b+GmE6FyK1120/0vFFC3coPGWxEp2gm0k22zGBjHHyOg7+AxgTqY0=', 'ground_truth/expected.json': 'eNqr5uVSUFBKrShITS5JTYnPzU9JzSlWslKoBokDZZzz8/LiffNzUiviTQ0NjAx1DcwNDOJTU5P1gkNcAxAKgUqD/EMigAJKBnoGBgZKOsjikSBxQwssMlHYdLhARJUgArVQCSVPZ5hLjI3MQC4xN8TvEqw2RuJwI9hOSwJOAVFAAogAnMI/qQ=='}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('connector_lib.PcbLib', 'C:\\Users\\user\\Desktop\\connector_lib.PcbLib')]


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
