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
INIT_MAP = [('README.txt', '/home/user/Desktop/README.txt'), ('stackup_seed.brd', '/home/user/Desktop/stackup_seed.brd')]


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
