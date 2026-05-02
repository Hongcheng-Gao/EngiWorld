from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\Administrator\Desktop')
BUNDLE = {'eval_inner.py': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('Board.PcbDoc', 'C:\\Users\\Administrator\\Desktop\\Board.PcbDoc'), ('IO.SchDoc', 'C:\\Users\\Administrator\\Desktop\\IO.SchDoc'), ('Indicators.SchDoc', 'C:\\Users\\Administrator\\Desktop\\Indicators.SchDoc'), ('Libraries\\Project.PcbLib', 'C:\\Users\\Administrator\\Desktop\\Libraries\\Project.PcbLib'), ('Libraries\\Project.SchLib', 'C:\\Users\\Administrator\\Desktop\\Libraries\\Project.SchLib'), ('MCU.SchDoc', 'C:\\Users\\Administrator\\Desktop\\MCU.SchDoc'), ('Power.SchDoc', 'C:\\Users\\Administrator\\Desktop\\Power.SchDoc'), ('Storage.SchDoc', 'C:\\Users\\Administrator\\Desktop\\Storage.SchDoc'), ('Top.SchDoc', 'C:\\Users\\Administrator\\Desktop\\Top.SchDoc'), ('broken.PrjPcb', 'C:\\Users\\Administrator\\Desktop\\broken.PrjPcb')]


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
