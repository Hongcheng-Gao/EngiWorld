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
INIT_MAP = [('README.txt', '/home/user/Desktop/README.txt'), ('mixed.sch', '/home/user/Desktop/mixed.sch'), ('rcl.lbr', '/home/user/Desktop/rcl.lbr')]


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
