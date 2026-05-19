from __future__ import annotations



import base64

import importlib.util

import shutil

import tempfile

import zlib

from pathlib import Path





DESKTOP = Path('C:\\Users\\user\\Desktop')

BUNDLE = {'eval_inner.py': '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'}

CALL_FUNC = 'eval_outputs'

CALL_ARGS = ['__DESKTOP_DIR__']

INIT_MAP = [('messy.dxf', 'C:\\Users\\user\\Desktop/messy.dxf')]





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

