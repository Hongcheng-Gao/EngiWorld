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
INIT_MAP = [('review.sch', '/home/user/Desktop/review.sch')]


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
