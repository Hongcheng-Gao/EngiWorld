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
INIT_MAP = [('blank.sch', '/home/user/Desktop/blank.sch'), ('info.txt', '/home/user/Desktop/info.txt')]


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
