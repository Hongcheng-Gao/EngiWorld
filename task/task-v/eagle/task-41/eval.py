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
INIT_MAP = [('bare.sch', '/home/user/Desktop/bare.sch')]


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
