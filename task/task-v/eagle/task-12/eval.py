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
INIT_MAP = [('topside.brd', '/home/user/Desktop/topside.brd')]


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
