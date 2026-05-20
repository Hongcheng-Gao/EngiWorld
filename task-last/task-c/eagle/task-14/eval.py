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
