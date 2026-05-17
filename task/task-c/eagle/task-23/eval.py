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
INIT_MAP = [('coin.brd', '/home/user/Desktop/coin.brd')]


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
