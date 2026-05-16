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

INIT_MAP = []





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

