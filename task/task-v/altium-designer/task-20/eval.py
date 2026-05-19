from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\user\Desktop')
BUNDLE = {'eval_inner.py': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('requirements.md', 'C:\\Users\\user\\Desktop\\requirements.md'), ('template.PCBDwf', 'C:\\Users\\user\\Desktop\\template.PCBDwf')]


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
