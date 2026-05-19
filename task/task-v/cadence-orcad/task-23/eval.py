from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\user\Desktop')
BUNDLE = {'eval_inner.py': 'eNqVVE1vnDAQvfMrXF+Kmyxpox4qFCKt1FQ5RlVOXbaOgwfiFoxlm2jV1f73jg3sEkWN1D3AzsybN59MbfuOcF4PfrDAOVGd6a0nQuveC6967ZJk0v1yvZ7/W0jq4GmEf2rV4+x2h2KS3N58vyFFFFKkVi0Ss8yC69tnSFlmhAXtk6/r+xsekRayqu8MAlNLN+vVj+1GrP5s95cH8kIq3Vkp95/OUV/KUubHB4r7zwfKkrv1/e0/OANHfrH5eXX9vqSl+7A9Q3ySSKgJ173tRKv+QOph53PivGVkdR3eeULwF9RIOqWcueExpVdBuqbn0ciWsCmLCGtF9ygF6fKxH13W2H4w6UfGMi06WHpbwCHoqMBumVZUkNLSlhpjUHyyDPNRJp3ThmfR8n7wZvAuHd9cKntKX6rKj/mP1nkoJ+xiLBEntEPQhL4gVJom8ztPo7EJBHG4aAllaMm9HfwTfQXF9MM+FGRPjXCO5uSbaB1WS0+xaUx0SoYdop+qCS5eSCODnXJYFxsLOJFuqAWBq0i3SF9T2BmoPMg56U45p3STk30gCS0+0AVD7PBINAdcTD+4IDuWhTNIQVe9RK6CDr5efcEpgLW9dQVVDfoAZYy8K5b+x0CN/y+e6Pd2pVSqujZCWdIIM/c36MA6Er/FYyfWbQs4nqBA0FvVz3HijEKUezvAC0v1BNXv0bahD1PY1TPBaT8cWy48whwRtQcbT8KFFB7I3Jd4R+g2eZ0D3hbsPw9TwttTYJWcd0JpzunYjPkc2QaPhoNkXFKD2cyqbG2bocN7chckO++xyYSUXEy2dLl2E8I2YdURGGkC1E3Oxip0Cecuk0NnXPriQwvAbPEFnROlJcYoLnGu2oUzKlylVBE3nrHkL44xvnM=', 'ground_truth/dpg.txt': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('HSD_FPGA_final.brd', r'C:\Users\user\Desktop\HSD_FPGA_final.brd')]


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



def _has_generated_python_file() -> bool:
    if not DESKTOP.exists():
        return False
    initial_python_names = {Path(rel).name for rel, _ in INIT_MAP if Path(rel).suffix.lower() == ".py"}
    allowed_names = {"eval.py"}
    allowed_names.update(initial_python_names)
    try:
        items = list(DESKTOP.iterdir())
    except Exception:
        return False
    for path in items:
        if path.name in allowed_names or path.name == "_runtime":
            continue
        try:
            if path.is_file() and path.suffix.lower() == ".py":
                return True
        except Exception:
            continue
    return False

def _run() -> bool:
    if _has_generated_python_file():
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
