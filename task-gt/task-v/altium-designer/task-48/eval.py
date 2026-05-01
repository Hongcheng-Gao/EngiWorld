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
INIT_MAP = [('prod_design.PrjPcb', 'C:\\Users\\Administrator\\Desktop\\prod_design.PrjPcb'), ('variant_spec.json', 'C:\\Users\\Administrator\\Desktop\\variant_spec.json')]


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
