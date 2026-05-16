from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': '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', 'ground_truth/tune_measure.txt': 'eNql1E1LAzEQBuCzC/sf5qiIYSYfk0lhD1tpRRCF7navSw8ehSLexP9ut0UQtM2wuQVmSB4mL9N9vO5hv3vfvcF9262gAYK6uto8tI/PQ/u0gM/NOJ2/GgAxFhFXt+jg2LNe/nSsl1OdjJzq/lgfxrYfw7ZbwHD9su1vGnCGxPlDA0LbQzA4td8h11VddX8gdjbEnm6+BPHsghbiCiA2B4ksUQvxBRB/GeINJhYtJBRAYg7CaFkL4bOQZEJZWK0RZnVG4myIIqwoQf01UgDJhtVRQi0kFUB8DhI4qSdCWCCJOUkS1EvO71Yy9PulOXFlTOrdSna2JJvXw9AkObXEFUhsTpKiV29X8gWSbGKJRZ+TUCDJJtaLtf9LvgGmOtY4', 'ground_truth/tune_result.json': 'eNqr5uVSUFBKSi0uiQ+Kd3NSslIwMjIwMNAz0EGWcHf09ANKWZoiZMLi/UND4hNL4k1Li4FSxnrGhpYQmcSk4vjUoqL8ovjcMKCMoaWeARIwNLKAKMtNTS0pjjcyyA2LLy5ITQaqLCkqTYXI5cUnJ+alZKYklqSCDDc05eWq5eUCAGH5K8A='}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('opt_target.cir', '/home/user/Desktop/opt_target.cir')]


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
