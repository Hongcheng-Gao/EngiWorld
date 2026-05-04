from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('C:\\Users\\Administrator\\Desktop')
BUNDLE = {'eval_inner.py': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('building.dae', 'C:\\Users\\Administrator\\Desktop/building.dae')]


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
