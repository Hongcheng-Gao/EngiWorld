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

BUNDLE = {'_shared/build_native_task.py': 'eNqVU0tPhDAQvpPwHyacIOKaeDKb4M09Gg/e1DSVDmxdaMl0quu/t+W1ajysPRCmfI/5pqUh24MQjWdPKATofrDEII2xLFlb49IkTebdN2fNWri9Z92lSRMVBsn7Tr8u9IdQRl6aKGyA0CELlu4glCaXL2/bEVfA5S2wHzp8imU5br5s0wTC0kZzhEIFCwuuIBu3G91hNsHav0AtWW+UYPK8n3G6WRU3eNSOXV7MTnFNkTbUMyHmC7JYue2ZzPYHbzHsD+GZD5LQsKseyWMJo5Swh7Esvoc5G04Yjs6sNuXMP42/tsOnMOEw33GcWe6spxqn6Zeg0PG3k7i3Brdr4nALYIL/lZqkdgi7oHlveRenfUdkaTaY+4v6mynG2ZnmccbOr2e1qdHiFOuDNKPA44A1oxLxbubxGq65JMstKF3z71wR9d+ORs5kyXjk/DSEaLxRvh9cHi3LcBIqiFXXQci4+FdJV2td7WTnsIALyJ5NVp74aGqrtGmrzHNzebN8Cr5fqAUoRg==',
 '_shared/native_altium.py': 'eNrVWFtv2zYUfg+Q/6DxSUpcI277sAXQCjdxi2CpUzjpsM32BFqiHC0yJVBU4iDOf985JCVRshOvGPYwA4FNniu/c+FhYpGtnCCIS1kKFgROssozIR3KeSapTDJeHB4cHpjdv4qM1wvBDg9ilM6pvE2TRSX6FZaGIh/zhC8rwoVkgi5ShgqvLkfBl+HnizPHdxZktj4/ma3PPs3Wg8FsPYLfQ/j+CH+DIawHBEUODyIWO4wX6CgH3+5ZkKXMRfOnyqrnvPnZGWecnR4eOPCJqKSgHxn6gtEoWDxKVriepiaxA2dUTP1CUiGLh0TeurVnntGCH0GTgjm/0rRkIyEy4cbkSanldMWenaRQqih3hqlMypUDSpwwg2OXPHKiLCxXjEviNcdQ7qRwCD7oHqCQwlgWDILCt/3vRyzMIuYSrYD0HIZOFT5JljwTzDaUU1GwIE9yFsQJS6PCLdgSvTlFQ8pglIRyCose7syN7awEjjYFoHx61tQ4E6hZOgl3jL5+kaeJdMmG2MAByMQnCp2EKxGLiJ8w43CGkjW7dz3nXkVN1Dp9OOLAa1jAuekd+nPfAgq2rURZS0FDGRThbaBCwcHJogt2mhRyiseszr07v4xtCUrBajd4hrpIs/CuUPR+nPAogXx3rRwis81kdHY1OfcHs03/6IP7wbd3NvXi3U+4+sMjvUYaTVvLOKXLwgdD12bT+NCc9NQ6G/g0nTeRW1EZ3mI8tMdWRNQGcCuO/lJkZe6eWMDrFNLR6aSVErVYI1ZANlIJ9nxVlA3pHutoaxdcxzza2le5Jlborw2sBed7jedscwMg+e70z838yJttxlCbenUMK0gh7WInARHYQHnUc7Ca8XBiZc4+8HrW6q3XFsUOoiR8h6jeQDq67cM2dto8LLXVnGkQdilq8NmlCuAOVjr3CkZFeGsD9O79FkDHFUDndZwsjFoFrFR3HGpFVzHUiLUiqpMRO0dbnsCFIVhMTk1K9ZcM6vwyWUxYzATjITSxXkeksQlizaLLdq8joYHvEsMK3wrOLsMaSIHMgoRLt+VaFqrrsP8b8bY8e9wn9PsOISghwB9SuQDpp+cuWdCHQAUDqOrbYnj+P1RHHf2pfdT5FNXMX8jipn31aZ4zHrn1jtdq9Q1j0/Gx0y8egyYzus2+uc7sjt+56aqGaV91aA0RfuVOsYFrFQfy6Wyw8nerwAyhgz7ecw1xbrTtv/PycBEoeM3dvPvas277f3HrGT+mYEphhd8AFQpV1/dsfXJCPDULbIgZGea7vRZlyl6+pJtZpHJc8Z/u5Ohcesav1yHqji6Tb5ejXy7G580IA+x7JxjlVJXAOwcwrw2eEtgNyD8YXbZRQaH/EJXrq2+Ts9H56Pri83h4czVpoeOAVvJ1eHMzmoy/Dzbl9ffApgR2w7bIqIgqyRfbgFUBrye5VrRnIK7Hqhca8Uf0abZRPRcasmfPf4ampz497Fkznh0Ac7+UOTxc2A6YsMSOWwPcwOvgpjkb4NBZEBeFVPVn4dVzjnoqO++ARb0Y9DWgfjobNamZgW0HtIbBKlVUE6TZA8POWG301Ub1LEP1NQsuKnI9brEU3mLNjIjQo6puHjetpJO/SNAduSpvgJwQrzb0g99xdm/qGteM3+Y5qMCh8ABsDI6HX0bbxhrR/a2laRitkGo4WgGlabrVTrfjua+VIOOLsap6v9BBeCUCCvdXQYfpFw1Y9wIMVPgPh5b7+FrXZdh97KtX8oOAolMdzEXRflRCh3BRqAfORdDR/Le96rajRZgk/icK6eRByZAZx5c0h6d1wpc+KWX85kf7KV1NeGpmsStAuQKUdr7DifXsD+lgbW8FTXUf8bhNrm0ZtNk6ZLm0/gvxksa/AR3nVXA=',
 'eval_inner.py': 'eNqtV0tv4zYQvutXcNVDJMBRtoseCgMu0C5SbIEegnbRi2EQjETb6sqUSlJJDMP/vTN8iJQtOwZaHxKRnPnm9Q0fa9nuCKXrXveSU0rqXddKTZgQrWa6boVKEjf3t2qF/1Z7laxRtWN629TPXu8Jhkny5fGPR7Iwgwyw6waQ80Jy1TYvPMuLjkkudAIgBeoXtVBc6uzjjCgtM9R2IuSBpFRt4btK8zyxJgX49cIpa3Td77xh/qYlKzVV5ZaWLcwJUFeEfEdE+w+bk8cfPn5KkqTiaxLW6Te+z3A0J1Vd6pzc/4QezBMCP8khJYLgcrHhOkshTMnXaU5aSdI0BmOSPTf8FAk/RlAHM8Cfx5pPwM+C1Atrej4SsjOxDKztIJSRlJ+L5dDJHddcqtT6mAX5aG1GDsfc6R1djBys0rbXXa9VZv/TqpYnQYYFX/pINBTfyDKhKFYeJCM1KDaI1Uq3kmI2mNwXf37+8vtvv6RGqxa19mqGYqBg5pBhKY6AKYIrxJZajXQ3Z5ob2faiolr2emuU+VvHS82rAomeusIZci3IAXKkMHO/skbxGUmD2zCJrI2ChbwZd9fAPT3EWvA3CE1l+XwoioVfQtQMTa7A0Hpww2WGYHBkVytVi82cHDzcMY1gDL0smrWt5T6YGRAXpoeLpmWVylxGoDIMsgD9k3FRthVYWaS9Xt//iB3nIUyao76CjEy0UW5JSNbQIeajFhcaMxtqCdnyRv5PfJ8mB8/fSt5p8mj+wa5GmMK5d0rRC+xrolswpDCHviaOnVAOALleCWCB4rbZrGs5+bAwUyc5vc6L1JkMSUIMUm6Z2EBle+GL3OxBvTFbpHXc98dVujAJGwHmGUwNfWD2BrcUb36TAoNfaR6zPyBfD2/UfJ7uTjuKGXAuBRIznZodTUXBLONNbmWjRhoB4CywGwl1Upai1nw36tqyxx3udOO30kvAW4W2eWaKn8gO8FFzrdENpMVUtpwEWgUJRByvXWSvaMW9S+A5eaaIA3QGyxGdLyc6tKzQteh5koxdXbqTaoU+hxq4yXEAk87/hZLIgx3T5XZONsClAwLfGYy71Qd5nJFXBqEcBvxoLU3eD8C76o/LE2eH6Rvc/WxlJx12OBdcjlevOT3iVOA3jk64HfE0yJlAJ8WwCwRMO9fMljrqovMOCMnzIrgTIIjZ3BDnRo4eUOk4kbYz4Ch5+PcsW++VOQa07Erz/0bOIZvvuH9nxO/yWwvMmqZ9hezbFjVnYfq1bbhkouRwQUufYFnih2NdepwoptlnTEhY0og0F8uJeih7Yv+8kkPT38iH4MqNrAiZNfyAxE0fdHBSHMKWeTMhzJUBDCmY5FVmjufBdbjVmtM5yhhOnSRltHkbvBtoE3wngr8G/ijCqgovfONwzO0CkN9njbdm7qho66t01fEr5ZaX3+zaMrwJ3OngL92jc7YzW4HecvfeIu42HT0pBlI+GEY++E2w7yqmbTyof3aIt6LZxziQW9KCpDw/pxQ4t2N4KlcwqkvWjC81FmWVTCQmgcpQivyBZ+0CrhiUIhKlqS2Vf+nKDRRCuROMdZAhP1X8LDc9RvSEI+nfLl0B5aLMrWXxU8BJyA12LQgaGBRVThlS3Tf4oBi9qVCgiB4QRrSTNaCbC3vV7zqVWV3sbMzF4tOMcKHw1c5UWdcL8zJxV3Z8WcNzA57UyE+r6J96QJGccJAl3+fJv5PNF6s=',
 'ground_truth/expected.json': 'eNqVjrEKwjAQhvdC3+EIOGn0IqSga2ehiOgooRwiNklJog7Fd/dSK7gKd8v33/cnQ1kAiGTChdK59bb3jlwSWxD1rpGIG15UldRiMV4+THenHCu8TYgtOzl7iteYfABOYb6SuNQzUGusQCOCPU1Gb4KxlChEloaMGB58R8G4dmzP4ueYk8Y/KWTKJd8OxvW/77Jz/P1+Zq+y4HkDM7g/ng==',
 'init_file/harness_parts.SCHLIB': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('harness_parts.SCHLIB', 'C:\\Users\\user\\Desktop\\harness_parts.SCHLIB')]


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
