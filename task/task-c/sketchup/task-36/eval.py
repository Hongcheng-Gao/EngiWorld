from __future__ import annotations



import base64

import importlib.util

import shutil

import tempfile

import zlib

from pathlib import Path





DESKTOP = Path('C:\\Users\\user\\Desktop')

BUNDLE = {'eval_inner.py': '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', 'collada.py': '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'}

CALL_FUNC = 'eval_outputs'

CALL_ARGS = ['__DESKTOP_DIR__']

INIT_MAP = [('orig.dae', 'C:\\Users\\user\\Desktop/orig.dae')]





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

