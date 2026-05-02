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
INIT_MAP = [('blank.brd', '/home/user/Desktop/blank.brd')]


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
