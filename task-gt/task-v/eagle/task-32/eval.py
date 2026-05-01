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
INIT_MAP = [('usb_breakout.brd', '/home/user/Desktop/usb_breakout.brd')]


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
