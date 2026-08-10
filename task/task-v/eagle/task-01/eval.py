from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')

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

BUNDLE = {'eval_inner.py': 'eNqtG+1y28bxP57iCncmgE2BFv3RDhvao1C0rIlju5TkdMZWIAg4ijcCAQYHSGIVzfQh+ip5gTxKn6S7e3f4IEBRTuJJReA+9nv3dhdX27YnV0FcBHmasRn8Lw/k5c7gJXPOCxFHLGAvXrxggcyD85iz81gklzxjMpzzRZCLkM2ydAGvWZCHc9ezrBMZXPChxeDfcpXP04RxAO8tV+zo5LsfDo+ODj+89/cPp5bVfGeLQuYsTJM8EAk704g8QHTGHCDrLEjktRn433/+y/I5Zxmf8YwnIbcusrRIIj/PinzeZ5HIeAgMrVghuaSlcZDnPHM9djwXkl1kQQRsLHkGLC8keyxhZ5gXWRDvWGkSrx4zoFpEwCJwAP8hiH/98I4wJymbTMc9/D04OaTfyd7BuwkTyVUa0haPHeYsWC5jwaUlxQ0DeYWXcmiRYHY9lJhY5r6QPuHxbxYxzhB8ePZ4nnHuTWK+4El+DM8sDBK2DDLJiZaZiLlHwAaekZr0QVU+rMkZK4EFOYs5qA+Y4OxbnHzFrucpgDmL+JUIueT5GUszi237p9efAcg8E+dFztkCtQ4CPnNeCxeQnymSnnlsHkg/4z8XoIgIHmYRrDIkIRGSJcGCR2y622PTQY+N4dd5N9nfBVLY/q4LI4PtJAUZZ0Ecs2UGbCQ5c8JA8h2QBE+kyMUVWQigdhVdzxVdsgDFrHy5Wpynsdwgqk/jMVMLiV4WJFG5YDthCOHg/X4DAr8RANu5EgFp8EzN7Z71HyB6tXZwxmJxngVg19cin7NSgUhtH/D12IfpA6Sm6FFWoHUD/o1KIbAaWP/o5KMW3AsluITnch0YCu7ViD1j38LsK8aVxUrwBeKyDBTbyXL4zRK8FqW8EIlYFAukpMcUXyfHmpaXHlvGQSEFxCM/C9F/ippxTXf70wHTg2SfrP/Tly/RE+fLFw9/3defL384ff3XB4gddT7eVcCMrW/f1UKXFIvlb7+evn4DSD3Ltm2LgqbvzwqIONz3mVgsU7KxJM0pfkjL0mMZN09yXuQiLt9W0jzmfLHEeGDeu+NHINnkWGFeBvkcDMmg/QivlgUAPZzw0H2y3HnaA6PIHJx0gFSA7/uuB46WxlfccWEtRN5c/7A+s8N0sUgT23UtfSag5g2OMca/KZdFnPcYHjjqmbFHED5/DoZs8vzpwLKO946+9w/32YjZPLiIORxEtmVN/U97704m/nQCExn3ANMS6HEy+yeStFdTq+1aj9hYG8AQToILAdb4hKVLlGsQg9OEYgG/taEiETnGkBkEaifpF/1lf9H/7Ve3vuaNNX4YFTVtAy1vDj9N/OpPey9ETbuHQ4cH7z9MJ+O9o4lrWVbEZwyEDkca+qp/vtJB1KHgOYQ4IPPPk2Oj4dMexdMhqsxlO69YNcV+Ye8hHKkjGYxvvB4i4zS9LJYsnUFg0AfE+Yqh1M4QZi3ee2i7COY6ALgjQulBZOKZ49I45g9LdH1FZekrYsacpXfBc8fGPbaLUd62XbOZjUYEc9jwroyDewAsq/aCrBjxxPwiCFc+V+kLd2RxvhBSgr58SABqsijNTcGHdUA8GXZzS828FU5YVm12MDPyRTTSRor+wZfkGSP0FIAFtk8bH7GPlJpQCIx4DGLOKH9C7v/BZnhmnQfhJctTVuU1TKaskcdoWMtAYhaDsTktMCIAFJFcqHCI+0bEErhgLWtSigLBQ0jBRR4dP9JxKxkHcV5trciw62qDNR07K8QwX47yWPI1DXo8y1IU46xOG9E0Q0bRVm6Bgju7S/OZkeaPaXapMk04OxdLUNVOmEJKCQILWKVDzJG+AW4XxQXEDiZFxHf4bAaHilTCouPNhEvvmGNsgtN036SLYIkQJvOo4uIaMWtjySO3HI8h0Ythgua7JE8ioojtIakOTPTUrgpIzm9QAzQKpheA3mHEKY1oZ2dHBU62O1T5KOWgO1/7j8Dl2apiK0tTxAxRAqUK1gv25CDyijg4RfwUeT/OCt4YBZ1igFZ88puQL3M2oR/UAQiQtxCR27YgvwnAYjpAozdx7YKeypw9SKZ5Ejm1c8Qpd6JXjeyOlNrulWvIiaKRwl0Nq5wDJmzKrclJQca1jQGUBUE8stNLGx1CE4+2DkatEnIy8iG71Rzc6d2uW/dBtbEmmYaNq5x4RPLyMO5DiHBsr9+nCfprd9jFYKgLtCrDlOyrzGIGsUlXDYj/8+m9gTzCNTqSl9mnCefVqqv1Va0lIJTW0eiB/LNw7kSSVm+ev1oLRXUejKE0jpuvtqVWRdW2pPM0jZ06ZrfLqho1hUq7G5l7Xz2p7BKckH0DGL9pm19DTSjKBAFSDK2srWUez4bMFGEm0Tel0gPNY72GAwuxp7uQsdjTAf4d0/N4YCu7oUAMXMCyhIwoQSNaByLuy20gk3EZlOgYMk41R1AYgqGHFGk4yA9O1qpW9JhzguUs7EE/w32qQ1DLfjWcsjrBwhFOYQmF1JxTpbKCCgeSoX/zLIViXcQRHLOespuYR7vA0X0k20iOrZZvX1wuBUEQcM0uFRzVa2XkWqzGcAnbLyWUr7DrjrK8bdkOilGj7DLqdXU+AZuo1GGftmNnrUa3TTw0pqIjqX6FKKqf7u6x6+dDU1mbIt7Bev0J1ooue5BhoySuwrBxCuHYBaigPrYpEqI8YeG9aW2VLYjz2lpdw1fL4/S6sZyirLMpzLbBU7x1OgNue/EjNi3gkNsbml4CnJyqE2H39dPAZnvv99tBCuxS9wa8eiCnUjJhTgkHTNwAWovUsNoGEDauj1QgK1+vhq3aulJSIwkxkICQOqTydQMkpdoGJC2M74a18IhVIFpTnzo4fXZ08pE5MU8ET8KV2+CcCiDVOsGw7hAzayxv4KFrNzLQsbuD7q7dQOf67kdsP8WM+DJJryHSCUi9s0DEqn8KCWeO2ZoMciFnK/TFxyq4PoaAGORrkK4DiaCCGBPVld4leOSZWgfiQyxCUTaj2DkHw/YaYDDC/J6Y1WzZdYQsI2WMoFpm289j1DJu6OjWtU/gWxvg20OjT7BxwKHf4eluc7R6MezskH1FkkaNt47kEMfxjz4IHrEjDplLhA1CrDGxxIRImUKkmkzHQs6pbQxGXlCnPQGZiCuRr9BpvpXiIgniV149Z0X4tZC3gQq18/cdRgizQ53gbg5OuSS5Tk2SSNe2a1WVuzfr5OWw6iKqnmHfdPrkww6QbOsxPy0P6MHWpQO9NNwKdWygXvlEgpPtqsBPxFdxH4u6JRS0oMqMUgqTHKkTV+fiAGRAQAZbgQzuAUJkO+FWSsJuSrRAVVVIiTUy55JzEpt/gXrztU3vVTPQo6RZL62B1TJvQhuU0AbboA3a0MImbWFJW9igbdyGFq7R9rVO0tHr7vAXJTskQfGNT0Rzl+vcNkIymumQ2dET6p/WYKvJwT2TY7Oz6nnWltx1hFDChQrradAo7p6GhMJaC6NVkWw9YpP3B4c/fpi+2wf5ftw7nE72ffruptuB4PH+UiQ+JCzSwSClD0MN47OTtFO1Hrs1eZMqsc1wOSqSVirlNrOLMkNMmoW7SMBzbffOrRVCmwP4qelq5mLBM78enuvMmDr9tpF3QjCryLi3hXCnekGIg4o5SmOJPnjo1TJdT+R8IZ01XintwpY1JXybU1RIxTfko6UUT+sHjSKo1RyhNLxHGFXxrGsDu+ICmFCbPz89rZ+VHeagBAhDMIUivCsTfM08FPykx8apR3IVpD5c0MpnqzmCi56nnz/D7ymGB2rNt1LSJo8zezlfSYFdRYSIgSEAFaUJW0BUEEtsHiNdoHmRrLVLG/gUOuU+aFA5jDqPg1gEkku3yReNIvV6uknkJRTFENVJvD21pNsFQAq4tpLCRmZh2bqOq6iosmSi1/70BKsITKfh5+/mHKVvnWbJlLoQk6PJMT0c0c9zvVTlzGohptUwZc5NOI0uyrljgnI8PTwwvwcTGjIHcj4HrPNq/Vu14S0gLh/e4tNLU/4L1RlX6/cPaRn8jN+WD3vTgwm+/E1vwa6+2fBPnPhwcqx/PqqnZ6UEdDcHzFfnoyoXJdHYQyWiMjeFv/CMDF/wDN7xqdfSja14TGPcop5hF/ERZBfcHiqeYAwIhdwRBuDhzvhvkKwc9YnUtDHQtPRI1fzx1OEFtrPJzcsmAHU0Z0US6m9v6BAL8AjVHzAAtRMA/2hyPWRWPYDBwkrt5cY3YNlpr3yDtbU3FEsZjswgSZLcV2NgKhCoHSQlmq2wbQxfZKTqgoucY+vJFB7a3upTyqA+vNu3K2tSbIHM13iiyRofsOK0cnzKHxOKfnzWFvpnhIWaosyyxzBYuj0MMjVHNqcACQYD8Ag/X840FtwNb6r47+wKuo1vgJiXN6lyUYKDzs9+pVGAwmd3SkTUojtP6SNOBmKHJaaQ4VH5xQv0VkNDaTjhuS1NpZTq3Wad7ZY3khA8qSxPWeW/m7ANDLaa6iobuQfhoImwxIRotaH016yjjX5cMlvhLF1jM/LxGrctfEgExtFNaActGW/HqRmOoGYt8HzTIiY0pvGKH5qot0qZh37SKYouH8xke6pM31Wftd1XXaMIwHekGbDTp9RghMki+Qq6ypCtOdBD/QfgqdgZJGmEPcQEP/o590EzJDTAqbzj1t5DX9t7/2F/ok65O9iHbOqCMsjnfwoaOom/J7/eO36rsQ3WsOl0TnGGiRW8aAo2Sp38GUVf+TTZxTmv+7ZJAITM0wxqY5Gtfa7Sgah980BP3FYR6s6QhjFoLblvtNSm6w01/C4kklojbplgPG7EtFbES+h+QyvK1VkxhSC5VaLTqzgNIlV2Ok6pxpFxLDpAbvWh0FMiv1MHbh2y23G3z9GWVx1tTVgaWRe0hpo1gff6U0uV6OJ4LQLPeJVPYM6RFhdzFrCwyPA60U4MwSvHTMCgt8sU0e8ugdYa9WW20b6vVe9B/7ES5s6kmn8KTaZ9/WfQVPrhivwcwVaiQ2VTIlHpv54HbAxiGxM3u3ZZUrVoTcujpXVcifXuJiorYdaoNBb/B6mstXi3UIkrSyo1FOy/AxBzE1odr7iKroAgtWju6BL0dbEeuqiw/+prSpm6ITfadtGpdEm1QV+50REOewChp9pEJL9QOzWuVE2otsDUtCp/sALIt16X6rpBtOHCCV2ZcBRcF20Zp2o+oWjt6Z4Rsr+pI7L5/slNONwMT5sDXTK5Cd2arO/pyqlmXFWT0MWAOklwtOhmnEa4/aLo2pcJbVgYFzuMywRCFRp5ZW32AzHpHpz6MTciGvq28Lu8j5z6Prqd7fuLAJzLt4dW7TzDi6Kgvav13H2ZiQQCU0H/B4D7L/+DsNS1OQAl8wgsttI/jvEbkTsDt+kGlflrAj7vnuqeDmHWOpTFYhHgVS41V4J7WnMRGaYZnX+73lOVKu661v8BLh5tPw==', 'common/schema.py': 'eJyNVF2O0zAQfq/UOwzhJRWQXfEYqWgrVCQkBKvuvpUqMsmYhnXtyHYRVYnEIbjIXoGjcBLGP2lSWpZNIiWefPPNj79xkiTj0fwrEws0W2HBlGvcMPj94yfYNYKxTFZMV6DRbrUEu2sQuNLAhAAkty2zmDU78tN1Y002HiWOkWu1gYpZVgpmDBqoN43Stjc9B16jqCKSaGv5uQPN5G48cvfVAT4e+Re8XmN5F1LNxyOgS7IN5pSnDsvGhaty+KSUCBb81mBpnY14YQrvlcTwh5V2y8Sp3SqBmsmSeLlQzMJ3//MII5UNYcnqCg7WCjkUBVmLIjUo+CQm6S5qpd0aB7+e3dwkUHNwkCxkDCgMQvJm9vZd0vs0TFvnsuTJch8I2hXsvZ8rvE1WPbgj7AqG2rg0fdKDPA68GWsalFXKk85juj8iaJPJKXto2uO5Az4yh8UTfZb50PbHk5PL9Nf9/tj9LLnfrwe50v0B2E6GFFH6CdDzzL+yL6qWqfef/Eup/UzFsJaZu6KuBlo1FpuC12Ko39IJ3OQgamOXA7WvSAV+YlLSGCNDwamZSu+mDhmzRa2VDqo8kizAU+qCdc24uZ1fA2cUtCKdA8m76sR71WjVoLa7XstBm0HK8OIV1NLmJ40x201adjJ2Z0NJuND1UM3kgQhWWSb+E0CgTB9JZ0qlsafz45ufGRHXKKAnKodygOkULv9SSIx/mV2eFj0Y3YsBzfAkoMZsmN716dDGDCKIWmIc7lvSRhzrKJM2j+sQo73Y9zHaqJK4PQCpLzvOmP/Os5ecVHzudPAaOa7TZ9JPAsB8sfiw6DLwHkdDdW6TH6KkutNycmakPso4Sx5OgD8nCfRs'}
CALL_FUNC = 'evaluate'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('README.txt', '/home/user/Desktop/README.txt'), ('led.lbr', '/home/user/Desktop/led.lbr'), ('linear.lbr', '/home/user/Desktop/linear.lbr'), ('rcl.lbr', '/home/user/Desktop/rcl.lbr'), ('supply1.lbr', '/home/user/Desktop/supply1.lbr')]


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
