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
INIT_MAP = [('README.txt', '/home/user/Desktop/README.txt'), ('board.sch', '/home/user/Desktop/board.sch')]


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
