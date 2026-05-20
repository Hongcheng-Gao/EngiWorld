from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': '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', 'common/schema.py': 'eJyNVF2O0zAQfq/UOwzhJRWQXfEYqWgrVCQkBKvuvpUqMsmYhnXtyHYRVYnEIbjIXoGjcBLGP2lSWpZNIiWefPPNj79xkiTj0fwrEws0W2HBlGvcMPj94yfYNYKxTFZMV6DRbrUEu2sQuNLAhAAkty2zmDU78tN1Y002HiWOkWu1gYpZVgpmDBqoN43Stjc9B16jqCKSaGv5uQPN5G48cvfVAT4e+Re8XmN5F1LNxyOgS7IN5pSnDsvGhaty+KSUCBb81mBpnY14YQrvlcTwh5V2y8Sp3SqBmsmSeLlQzMJ3//MII5UNYcnqCg7WCjkUBVmLIjUo+CQm6S5qpd0aB7+e3dwkUHNwkCxkDCgMQvJm9vZd0vs0TFvnsuTJch8I2hXsvZ8rvE1WPbgj7AqG2rg0fdKDPA68GWsalFXKk85juj8iaJPJKXto2uO5Az4yh8UTfZb50PbHk5PL9Nf9/tj9LLnfrwe50v0B2E6GFFH6CdDzzL+yL6qWqfef/Eup/UzFsJaZu6KuBlo1FpuC12Ko39IJ3OQgamOXA7WvSAV+YlLSGCNDwamZSu+mDhmzRa2VDqo8kizAU+qCdc24uZ1fA2cUtCKdA8m76sR71WjVoLa7XstBm0HK8OIV1NLmJ40x201adjJ2Z0NJuND1UM3kgQhWWSb+E0CgTB9JZ0qlsafz45ufGRHXKKAnKodygOkULv9SSIx/mV2eFj0Y3YsBzfAkoMZsmN716dDGDCKIWmIc7lvSRhzrKJM2j+sQo73Y9zHaqJK4PQCpLzvOmP/Os5ecVHzudPAaOa7TZ9JPAsB8sfiw6DLwHkdDdW6TH6KkutNycmakPso4Sx5OgD8nCfRs'}
CALL_FUNC = 'evaluate'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('dense.brd', '/home/user/Desktop/dense.brd')]


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
