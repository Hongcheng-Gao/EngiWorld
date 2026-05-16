from __future__ import annotations



import base64

import importlib.util

import shutil

import tempfile

import zlib

from pathlib import Path





DESKTOP = Path('C:\\Users\\Administrator\\Desktop')

BUNDLE = {'eval_inner.py': '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'}

CALL_FUNC = 'eval_outputs'

CALL_ARGS = ['__DESKTOP_DIR__']

INIT_MAP = [('product.dae', 'C:\\Users\\Administrator\\Desktop/product.dae')]





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

