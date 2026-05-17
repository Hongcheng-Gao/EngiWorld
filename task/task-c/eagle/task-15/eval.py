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
INIT_MAP = [('assembled.brd', '/home/user/Desktop/assembled.brd')]


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
