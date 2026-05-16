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

INIT_MAP = [('materials.json', 'C:\\Users\\Administrator\\Desktop/materials.json'), ('rooms.dae', 'C:\\Users\\Administrator\\Desktop/rooms.dae'), ('tex/brass.png', 'C:\\Users\\Administrator\\Desktop/tex/brass.png'), ('tex/concrete.png', 'C:\\Users\\Administrator\\Desktop/tex/concrete.png'), ('tex/glass.png', 'C:\\Users\\Administrator\\Desktop/tex/glass.png'), ('tex/marble.png', 'C:\\Users\\Administrator\\Desktop/tex/marble.png'), ('tex/oak.png', 'C:\\Users\\Administrator\\Desktop/tex/oak.png')]





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

