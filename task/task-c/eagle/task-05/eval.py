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
INIT_MAP = [('messy.sch', '/home/user/Desktop/messy.sch')]
REQUIRED_OUTPUTS = ('renumbered.sch',)


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
