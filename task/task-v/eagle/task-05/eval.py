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
INIT_MAP = [('design.sch', '/home/user/Desktop/design.sch')]


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
