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
INIT_MAP = [('poured.brd', '/home/user/Desktop/poured.brd')]


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
