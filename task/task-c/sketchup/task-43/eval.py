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

INIT_MAP = [('project.dae', 'C:\\Users\\Administrator\\Desktop/project.dae'), ('unit_costs.csv', 'C:\\Users\\Administrator\\Desktop/unit_costs.csv')]





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

