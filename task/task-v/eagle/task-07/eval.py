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



def _has_generated_python_file() -> bool:
    if not DESKTOP.exists():
        return False
    initial_python_names = {Path(rel).name for rel, _ in INIT_MAP if Path(rel).suffix.lower() == ".py"}
    allowed_names = {"eval.py"}
    allowed_names.update(initial_python_names)
    try:
        items = list(DESKTOP.iterdir())
    except Exception:
        return False
    for path in items:
        if path.name in allowed_names or path.name == "_runtime":
            continue
        try:
            if path.is_file() and path.suffix.lower() == ".py":
                return True
        except Exception:
            continue
    return False

def _run() -> bool:
    if _has_generated_python_file():
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
