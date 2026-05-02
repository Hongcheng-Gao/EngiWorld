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
INIT_MAP = [('violating.brd', '/home/user/Desktop/violating.brd')]


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
