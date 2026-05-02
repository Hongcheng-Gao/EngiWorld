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
INIT_MAP = [('legacy.sch', '/home/user/Desktop/legacy.sch')]


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
