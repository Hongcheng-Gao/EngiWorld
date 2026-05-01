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
CALL_ARGS = ['C:\\Users\\Administrator\\Desktop\\output.obj']
INIT_MAP = [('scene.obj', 'C:\\Users\\Administrator\\Desktop\\scene.obj')]


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
    print("true" if _run() else "false")
