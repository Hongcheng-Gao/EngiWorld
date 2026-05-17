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
INIT_MAP = [('board.brd', '/home/user/Desktop/board.brd'), ('testpad.lbr', '/home/user/Desktop/testpad.lbr')]


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
