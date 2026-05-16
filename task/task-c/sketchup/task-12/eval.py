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

