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
INIT_MAP = [('board.brd', '/home/user/Desktop/board.brd')]
REQUIRED_OUTPUTS = ('annotated.brd',)


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
