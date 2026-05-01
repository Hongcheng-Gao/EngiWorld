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
INIT_MAP = [('mylib_opamp.lbr', '/home/user/Desktop/mylib_opamp.lbr')]


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
