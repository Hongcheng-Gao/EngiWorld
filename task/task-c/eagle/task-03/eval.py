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
REQUIRED_OUTPUTS = ('poured.brd',)


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
