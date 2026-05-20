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
INIT_MAP = [('proj.brd', '/home/user/Desktop/proj.brd'), ('proj.sch', '/home/user/Desktop/proj.sch')]


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
