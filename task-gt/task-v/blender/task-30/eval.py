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
CALL_ARGS = ['C:\\Users\\Administrator\\Desktop\\part.stl']
INIT_MAP = [('scene.blend', 'C:\\Users\\Administrator\\Desktop\\scene.blend'), ('stub.stl', 'C:\\Users\\Administrator\\Desktop\\stub.stl')]


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
