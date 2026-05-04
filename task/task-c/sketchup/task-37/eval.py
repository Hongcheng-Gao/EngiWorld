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
INIT_MAP = [('mesh.dae', 'C:\\Users\\Administrator\\Desktop/mesh.dae')]


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
