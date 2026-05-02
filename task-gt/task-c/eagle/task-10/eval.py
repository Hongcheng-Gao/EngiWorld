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
INIT_MAP = [('routed.brd', '/home/user/Desktop/routed.brd')]


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
