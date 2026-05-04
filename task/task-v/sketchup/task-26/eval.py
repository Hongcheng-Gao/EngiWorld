from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\Administrator\Desktop')
BUNDLE = {'eval_inner.py': 'eNqNV+tq5DYU/u+nULU/xg6OSZbSLtMGNs1O6NJbaJZQSAeh2PKMG49tJM0mw2DoQ/QJ+yQ950i+7cxADYkt6Vy+c9dwzhefZbmVttYsh7/7n84fzt9+w/79+x/2w2+/MPVqtUxtUVcJ5zzIdb1hQuRbu9VKCFZsmlpbJquqthKpTBB0e3rVSG1Ut07N5+6zNk5QJq1MS2mMMp2kfitmeaHKLAiCxR93i5tPiw/siu0DBg+/WctC8zn7OnbrD8o8j5a3Ralu5FNRKQu7b/3uXSkrv25B6vteU0D/2c1apc9zoq3kRs2ZsZpWDQLM5uyprkva2JiVOz0i5T6tNSjXmZOUolAzZ2VhLOAnk8JM5XJbWpGDY2u9u8LDKCB6OGIyy0KjyjwmHLHXH6PamJ2diciJxgfJEqcjkU2jqiwkM8IDzsgreN/oulHa7gZ1ZSkcIWkdSdcKolyR3eFIUwThzpAtTBPHSJmTsqIaAzqp0EKqlMKgo05ovEwuWJE7YQM8pkqj2EVyMbhKg8VKfymlhMgb8PYjP+fsjH37btkfHQM6MPbMnTNzztjjfnZ3fX8/Q0S9wQRldnv98edZu4TkmoiYPDnfpwkl1Pdv37UMFhCNlkfBUYUd4hPHiOd3ZSB55mwE66ijPLqT4HIeUgywrEjAKC7z5DJvoxFIHxj+Z8WTv+qiCgkWhDjAMChoIaLe2mZrTejeIiu0D4lJQUVfF2Hki8quYbs2CX45mQNnzLhbJNA1PAywE5pMz6FeoWpMiN/jgkgTLB+eQwsQjoTH7FaCQ6ChjISSrLzeYiZbtkcx7aG9JqUdq3eDipcCkENKV043k4bl0xTS9QumH5Z1CKoSrSRmaR45+eo1VY1lC3pBy0QJ6tAE4BTUQCcW0A5TWtcaUkB9pU+jPirok96SnH0JBiDQqCW83Jer9zJuHUJaSyOIuAfE1aaxO3Zz/3AUBm29YT+SA2ixpk/wDsp5vFiOkfYCuKMSkDNapZbH/UnHjsWd1jAyKlVZgeUFmGBnCy1+OZDnfAXG7B1XG4PrG5AHFfI4m3LPYjYj7tnSa/P+eKqzXYf2cu7ggkxioh6jwQhqKxrbCpGDD/XSh7rpKQ2MN+ix3TRLntXOhF1bPvAAKBQESECzFbUG/CM3jBBcDUoO7O7J2u8G0/c9fctCWTZr+aRskcoymlr+ht0pfY6EjICYoGugtAfG9oLmk/7aO2JaFegVmhzkMcBNTfGgN01qbfxU4MOisqF+vFxGBxS+qB7gLqMWVB1HhXg/Q/6j9ta5eFxfVV2dgxa1giyjQzbbo8Z2xqOjEp+gup+DE3qCExNhovyUtVesy5VHpF/GJ6RRqKtxdu+njO0RHYfGTA3BETJ14f9wHZYJpYAj6XrKqB/QuNhIaPa+aVNjwn7QXReTa73abqAu7+ikHxe4QABC+nOYlecwKgCBv09d/Qr17MiBBkvOc9EL+UzYjxJcJcA+2Jg5ELQbHLrA30/NemuLMmYWGh8Omf7cbhoQ0G0nm+cMv8PBzyt7MO/8AhSiv/q1fDL4DuGejWNMRFF8+n7B+ErjGBNWb+0au6CszAtYPUxOih7hTtK62YUrG0+BAPYvJm40cQucD5N8MuwzHx6NlQkZ4i9knt8H3l3m0oMbyiXkA5wIaiLwYwIynguB2SEEd57XsgDC+50BZy5eCxu63ImC/wAQeaa8'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('office.dae', 'C:\\Users\\Administrator\\Desktop\\office.dae')]


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
    finally:
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("True" if _run() else "False")
