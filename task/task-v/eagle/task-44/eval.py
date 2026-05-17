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
INIT_MAP = [('prototype.brd', '/home/user/Desktop/prototype.brd')]


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
