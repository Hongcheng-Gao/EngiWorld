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
INIT_MAP = [('broken_amp.sch', '/home/user/Desktop/broken_amp.sch')]


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
