from __future__ import annotations



import base64

import importlib.util

import os

import shutil

import tempfile

import zlib

from pathlib import Path





DESKTOP = Path('C:\\Users\\Administrator\\Desktop')

SKETCHUP_INSTALL_PATH = r"D:\sketchup\SketchUp"

SKETCHUP_EXE_PATH = r"D:\sketchup\SketchUp\SketchUp.exe"

SKETCHUP_TEMPLATE_PATH = r"D:\sketchup\SketchUp\resources\en-US\Templates\Temp01a - Simple.skp"

TASK_NAME = "task-01"

BUNDLE = {'eval_inner.py': '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'}

CALL_FUNC = 'eval_outputs'

CALL_ARGS = ['__DESKTOP_DIR__']

INIT_MAP = [('params.json', 'C:\\Users\\Administrator\\Desktop/params.json')]





SKETCHUP_BRIDGE_PAYLOAD = 'eJydV1tv2zYUfvevYB2glrZMtbE3I12Rrm6QtYkDO9kwZIHASLTNWiI1kkrsJP7vOyRFiYov6/ZiS+R3Ds/1O5Qgf5dUENT7JjnrdTo5T8uMoBGb00cusnS6JCpZlMU1lsv+4KOg6Zx0ELoYfxqh92h0+fttb3R5dv7HePL1U3x9Ov3SH8R6s3cHqOnNxcXp5M/4t+n4ci/aBxmpq9PJ6cX0sJCHMTLjm+urm+t4+uVqr0gDMRKjyWQ8ib+Oz/YK1AjAg0BKZkiSbBZlfB4TIbgIciIlnpMQdhESRJWCoZJlsOqpf/sWvanfIpIXav2hYyQ+04xEj4IqEtSAY9Q9eq70bv5iXa1bEJmUBE0VZikW6UifbRQwmsE/YWnLPsXjPHjAWVkZZh7Nqv6Z7ZAoOGUqhk0cmEcrd2sUmYVoFR4j73Xdfn0K73ZoTXiWkUTFM5wQGRCmqKJEgqDATM64yI+R2bKnuf2I4GSBUo5ezMr6xewilGBJLGhdrTwuCEOuPofDz6Cr2kGoUBLyauERLxURccZ5ET0QoSicGeW4MIfoBbJ6qQVBtAmG3YTwSDCNs6i2PKifwrAW1f67Z+MYOjkxhlQlAY8u/TsdOBO8LGoNO6K3jnYEEf3g3KyXsDa2Fdyts37lecEZCJ4zCWXlRW7nuZBTymwM/r8JLj72f6taMoJFLDhXsTsiADIimRU3j/XhupDxvkphZKVczCu7oAVoWnUdQvdkTpmXNhtaAQX2plrd23FN1/27R/clzdIYwkuFLl5LEphCGfdyKiVlc5/qes5kn/6AOwxJkBWV6kPgbYW71HkU57R5xKiJqHltMVGBBc51x2jVEbxJEpiDBcFp61h7LgNoYIVue4ornMUCLInz3p3hGKiIQb/fj/roHXKwHK8sqIBmlIoUce7gYZSQKqgaAcoP6X6HbPJEybaRJdsGqgVNlkxHw4Nrz+J6p7EFpKzpRvSRpmqxJWZW63M6TYEC0vVYhBNFH8Bsve6VMNSDUDGHIJgeCXr1qEV2xqKPum56ur8cgx/oDZuOSFGYGaYXqGuDVR+soZAJiIlbGui8UfQjGoStjbXGOp/hVeOMk9XC0ytBKh1hPGlJ2P6pibJrM8vBt3XfnBGeD4dXml5/TiNGHoNVP4IhsDa/T/AbHh8CD/47ePB94P4rcIW9c55oGgNXXnEQTlPDkgE4GnpIaBoYHEAmiM7sAtOMmEVP6AT1fWBRykVRZllQx84dXnGJK5qE5zn1qsbu8WVtlMRQagkv1kHT4T5FdGcY2jmFoY00FB09N7hN15EFX1rFYHfr6qaZw19ojzHvGlMH2Uc3obfsAhcltY7nhGlnPBmEnr1n6/oQ9V7RaO+4BYLZXpQqlsti6HGdB9nUzy5HTYS3ORtGh8Bu+nVcokwd39lWbI3Hnc3ujUhba9etqahLrjUZX5F46z7sMvNd6Xh9qezsz8XhTPh5qLLQCkwrB2ZliJqI+VG3HoY7Ip1SWWAIno2qvtzpzwZLuvquspV3N7x3TFUr0DbRjeithJKsJq+qN0omy6LgcNdLjbvQHdqWiDJZQK43Xa9gdt0M0PtfkFXZfBrALZ7AnQZLuRki/dzc6Y+eT4XA64BE9zhZavNIGH0DPgq6+sK/6dpwyVJYpXWRwZeaqiJponlzXk0Tzf4iGER9XVfgXgiTQH/iHPqIaxKgdf0DUFA/TA=='





def _decode(payload: str) -> bytes:

    return zlib.decompress(base64.b64decode(payload.encode("ascii")))





def _materialize_bundle(root: Path) -> None:

    for rel, payload in BUNDLE.items():

        path = root / rel

        path.parent.mkdir(parents=True, exist_ok=True)

        path.write_bytes(_decode(payload))

    for dirname in ("init_file", "ground_truth", "_internal"):

        (root / dirname).mkdir(parents=True, exist_ok=True)

    bridge_path = root / "_internal" / "sketchup_bridge.rb"

    bridge_path.parent.mkdir(parents=True, exist_ok=True)

    bridge_path.write_bytes(_decode(SKETCHUP_BRIDGE_PAYLOAD))

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





def _apply_runtime_env() -> None:

    os.environ["ENGIWORLD_SKETCHUP_INSTALL_PATH"] = SKETCHUP_INSTALL_PATH

    os.environ["ENGIWORLD_SKETCHUP_EXE"] = SKETCHUP_EXE_PATH

    os.environ["ENGIWORLD_SKETCHUP_TEMPLATE_PATH"] = SKETCHUP_TEMPLATE_PATH





def _run() -> bool:

    runtime_base = Path(__file__).resolve().parent / "_runtime"

    runtime_base.mkdir(parents=True, exist_ok=True)

    root = runtime_base / TASK_NAME

    if root.exists():

        shutil.rmtree(root, ignore_errors=True)

    root.mkdir(parents=True, exist_ok=False)

    try:

        _materialize_bundle(root)

        _apply_runtime_env()

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

