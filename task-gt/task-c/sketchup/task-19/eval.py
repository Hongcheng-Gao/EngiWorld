from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('C:\\Users\\Administrator\\Desktop')
BUNDLE = {'eval_inner.py': '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', 'collada.py': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('tex/brick.png', 'C:\\Users\\Administrator\\Desktop/tex/brick.png'), ('wall_blank.dae', 'C:\\Users\\Administrator\\Desktop/wall_blank.dae')]


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
