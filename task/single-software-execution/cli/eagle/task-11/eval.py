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
INIT_MAP = [('drifted.brd', '/home/user/Desktop/drifted.brd')]
REQUIRED_OUTPUTS = ('orthogonal.brd',)


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
    if not all((DESKTOP / rel).is_file() for rel in REQUIRED_OUTPUTS):
        return False
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
