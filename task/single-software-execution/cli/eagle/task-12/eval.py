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
INIT_MAP = [('fab_capability.md', '/home/user/Desktop/fab_capability.md')]
REQUIRED_OUTPUTS = ('hdi_6layer.dru',)


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
