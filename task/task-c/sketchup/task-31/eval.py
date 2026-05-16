from __future__ import annotations



import base64

import importlib.util

import shutil

import tempfile

import zlib

from pathlib import Path





DESKTOP = Path('C:\\Users\\Administrator\\Desktop')

BUNDLE = {'eval_inner.py': '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', 'collada.py': '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'}

CALL_FUNC = 'eval_outputs'

CALL_ARGS = ['__DESKTOP_DIR__']

INIT_MAP = [('params.json', 'C:\\Users\\Administrator\\Desktop/params.json')]





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

