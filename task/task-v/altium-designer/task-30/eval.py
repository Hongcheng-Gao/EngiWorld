from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\Administrator\Desktop')
BUNDLE = {'eval_inner.py': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('base.SchDot', 'C:\\Users\\Administrator\\Desktop\\base.SchDot'), ('metadata.json', 'C:\\Users\\Administrator\\Desktop\\metadata.json')]


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
