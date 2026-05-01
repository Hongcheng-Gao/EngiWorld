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
INIT_MAP = [('body.brd', '/home/user/Desktop/body.brd')]


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
