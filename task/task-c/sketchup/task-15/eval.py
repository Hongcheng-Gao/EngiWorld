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
INIT_MAP = [('house_raw.dae', 'C:\\Users\\Administrator\\Desktop/house_raw.dae')]


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
