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
INIT_MAP = [('partA.sch', '/home/user/Desktop/partA.sch'), ('partB.sch', '/home/user/Desktop/partB.sch')]


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
