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
INIT_MAP = [('README.txt', '/home/user/Desktop/README.txt')]


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
