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
INIT_MAP = [('targets.txt', '/home/user/Desktop/targets.txt'), ('vias.brd', '/home/user/Desktop/vias.brd')]


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
