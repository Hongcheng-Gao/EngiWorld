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
INIT_MAP = [('mystery.brd', '/home/user/Desktop/mystery.brd')]


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
    print("true" if _run() else "false")
