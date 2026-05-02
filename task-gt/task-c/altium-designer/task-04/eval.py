from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('C:\\Users\\Administrator\\Desktop')
BUNDLE = {'_internal_native.py': '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', 'eval_inner.py': 'eNrNUl2Lm0AUfZ9fMeyLCaQLPrS0CxaM3mynmNH1o+1SlsHomAzomI7jsrDuf6/mu0n60qcOiHjvOcd7z5xC1RVmrGh1qzhjWFTrWmmcSlnrVItaNggVA2ad6lUpFntA0H/uOkxIzZVMSyZ7xjPfQ/hzWrap5rsyy+sMIfgRgBODy2bEA2xhoxJSrDPGJddMtSVvboNs4daZgUJ4SEgIbo/6aVB7DtZLJJb9fxqWmGb/GBN8Ezl+AGavGkIUEZ9aRO5QTpk2zcg454xvJnirNk91tuK5x+VSrxoGFGL2JYg6oPbUA9eKwwS6ICR+SOJHy+wcfz4HGltdQslDAsS1PO/r/ffZt7hzYUYouNNHz78nju25vpNssDPbi6CLfQ9CmzpgmZ9uP3x8X4nSeEIzP5wS1wU6LPh0WJc5fkLjqC/SWvKjYZf91+uu3GHz34zZEP8Hb/pB3k6SsvfpZPM3hFDOi03GWN3qdaub0fbNcqHG+N1nnItM3yHcH8X7dMtrgRxt+sMZAn2qMDl0/ojssby/j2OlqNVC5DmXrFDpsuJSN9Zh+CNM8V+tUDw/oFhWtwP27IaPDP6y5pm+wvhbOK5RL4a7EDk3eqsyRr8BZMpKcQ=='}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('broken_minipc_enet.PcbDoc', 'C:\\Users\\Administrator\\Desktop/broken_minipc_enet.PcbDoc')]


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
