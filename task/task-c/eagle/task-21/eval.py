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
INIT_MAP = [('poured.brd', '/home/user/Desktop/poured.brd')]


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
