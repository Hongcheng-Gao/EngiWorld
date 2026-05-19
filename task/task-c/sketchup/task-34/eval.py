from __future__ import annotations



import base64

import importlib.util

import shutil

import tempfile

import zlib

from pathlib import Path





DESKTOP = Path('C:\\Users\\user\\Desktop')

BUNDLE = {'eval_inner.py': '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', 'collada.py': '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', 'ifcopenshell.py': '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'}

CALL_FUNC = 'eval_outputs'

CALL_ARGS = ['__DESKTOP_DIR__']

INIT_MAP = [('tagged_building.dae', 'C:\\Users\\user\\Desktop/tagged_building.dae')]





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

    spec.loader.exec_module(module)

    module.__engiworld_bundle_paths__ = added_paths

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

