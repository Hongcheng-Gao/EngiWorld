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
INIT_MAP = [('amp1.sch', '/home/user/Desktop/amp1.sch')]


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
