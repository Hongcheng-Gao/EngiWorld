from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


def _push_utf8_text_io():
    import builtins
    import pathlib

    orig_open = builtins.open
    orig_read_text = pathlib.Path.read_text

    def patched_open(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        if 'b' not in mode and encoding is None:
            encoding = 'utf-8'
        return orig_open(file, mode, buffering, encoding, errors, newline, closefd, opener)

    def patched_read_text(self, encoding=None, errors=None):
        if encoding is None:
            encoding = 'utf-8'
        return orig_read_text(self, encoding=encoding, errors=errors)

    builtins.open = patched_open
    pathlib.Path.read_text = patched_read_text
    return orig_open, orig_read_text


def _pop_utf8_text_io(state):
    import builtins
    import pathlib

    orig_open, orig_read_text = state
    builtins.open = orig_open
    pathlib.Path.read_text = orig_read_text


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'common/__init__.py': 'eNoDAAAAAAE=', 'common/sexp.py': 'eNqtV0tv4zYQvhvwf5hqD5JaR9nt0akXKIpsD213F92iQBEHMi1RazYSpZJUEqPtf+8MSUcP27GzaA6OxHl9881wSAVB8IuQomIl6Av+2CiutaglNExprqCoFfwkfmA5FKLkGqLkTmQsT3W2gUvwL022hsvpxL/lqu1EVZ13L3pbxcl0Mp38qFhVMQVCA4OfhW5At2vNzXw6AfzTiAP/zRfATF3BPxBGoV38GsI4dDpWYnW0UUJ+Ri10v65LfJBtteaKAn2yMoyiOOR1uy75xV9tbXgOD8JsYLUMVsBkjg/LFXCdsYbrBD5ZR85qjT/TianvuETJe+vZSRQ3rZLoimkoypqZSyFNQumYfYWPW7Op5XRSWunDptYcGVXaAC95xaUhLsy2QZ7KcousuGSQrSAIppNCYbZpWrTokacpiKqplUHosjbMYL201yEXSIaXfy+3xMJ0kvPCVTQy/NHMibMYLt4CwfGkY5yPpIFOh53g+L3y6YDZcDB1c1Hye15aB4mFSD4aWEBqvSgbKPbLib4TTfqgI7/gXTWJxZRSMBINkKZIxDloScpZBXXRg9VPQJ/EV7cGBTe3R9A+bLD1cVnAd1ByGaFC7GF464Q1DZd5NEwo7nSOMYC2XdqFkLnNWtY5n8GGs9zl3uX8h+BlDpii2lo2jnYSFslvhxX5Wc0wYtYqLZCdbUeIKFBbSG2YzLiPS377+aEOCew+GSnfvL6dueqQ0K/AYuGwdy7ob2uhk063TtMlQ3bRsbSigza2sZ/IsfqOnbjPHTIwJm4GKGJtiS2EOwFL/L6WvMfmr11HOwZzgSwZD8nyi8kqQzvKzQvL5YA+3ICnKfTV9mjc+nO5D8viM7ZOLdHO7OnpOOc+rtUa9N0Tkh1/96xs+Uv5e4cprCJSh/vYtph1fn+FrYhd6Y07uiS6GBcq7pikxqUIgG5pn8kYN9y3J2j0a/Lmza3LJiuZ1rtd7o0pwzTFY86kaaR5Wcygmyy9ACRKNKIk6WhZ4PJrCrBzuNvRJO07cePC27iJ4fzGo+pk6NFJbpz27VCOnGSJ0Lph2ARj4x6ubxbwZijkJdlSU4RX4RzgFTYP8prVlR0QkbInG049zQoe7zs+noLtuiFo+ArDLGV4AOAJkJofsFnjNL/r89wbqWOqHZDhZPXM+bBvF88UQDGBbfo7tf61UrWKglZiHBwBeGhff3gX9Fw+V6wnsqPw8Aa0FqlLhLbxCKszDs4wdmdx3/yAEl2N3HH61Pu90GMOcbdwvCqMauqy2dsCwyoOz82ucX5T7biyxyr1gmodq5jhqhKSUc0oweCI92FucfiS/TQ+sfvrvePf2o9uAHtF8CU8vwzBqTKs2+JgGf6nEWRBLJcvJkw+mhPePfgdfX+HOETsKJlBaOyjoceAHgN6IhT299/kM8dT5NHMKEwcf9lsDL60CcIw+bMWMkLw8XlDrcsyOxfsiV53fRQcajE7APZmJd1kdgUR5/SKv9SNm7I7kmC5n8qB88FekZC0KN4j/GDi9mOr1zoEfL7XQK9wzGzpU48rkfWM1Xa+18NhEhIC5xhvFyEfvV937/OjVbcfeZFVig9Oavz+2xPzx4w3plfGw0PeQcGk6HvTX92nk/8AqENGEw==', 'eval_inner.py': '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', 'schema.py': 'eNqNVG1u00AQ/R8pdxjMH0eAW/HTUlAjFCQkBFXafyWyFnuWmm52rd0NIgqWOAQX6RU4Cidh9sOx06ShjiXH4zdv3ozfOEmS8Wj+nYkFmrWwYMpbXDH4++s32FsEY5msmK5Ao11rCXbTIHClgQkBSGlrZjFrNpSn68aabDxKHCPXagUVs6wUzBg0UK8apW0fegm8RlFFJNHW8msHmsnNeOR+Fzv4eOQv8PYWy7sgNR+PgA7JVpiTTh1uG1euyuGLUiJE8EeDpXUx4oUpfFQSwxNW2jUTh3GrBGomS+LlQjELP/3DPYxUNpSlqGs4RCvkUBQULYrUoOCTKNIdNEq7Ng5+Obu6SqDm4CBZUAwoDELybvb+Q9LnNExbl3LDk5ttIGiXsPV5rvE2WfbgjrBrGGrjZHrRAx073ow1Dcoq5UmXMd3uEbTJ5JA9DO3p3AEfmcPNM32UeTf2p5NTyvTP/XY//Si5f18nudLtDthOhhTR+gnQ+cJfsm+qlqnPnzzm1H6nYlnLzF1RVwOvGotNwWsx9G/pDG5yELWxNwO3L8kFfmNS8hijQMFpmEpvpg4Z1aLWSgdX7lkW4DlNwbphXF3PL4EzKlqRz4HsXXXmvWi0alDbTe/l4M1gZXj1Bmpp84PBmPUqLTsbu29DSbgw9dDN5EQFqywT/ykgUKZPpDOl0tjT+fXNj6yIGxTQGZ1DGmA6hfMHDon1z7Pzw6YHq3s2oBl+CWgwK6Y3vRx6MYMKopYYl/uavBHXOtqkzeN9qNGebfsabXRJfD0AqW877pj/n2evObl4+UjrD/r0SvpNAJgvFp8WnQKfsbdUx17yKUrqOy0nR1bqs4y75OEE+AcnCfRs'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('board.kicad_pcb', '/home/user/Desktop/board.kicad_pcb'), ('enclosure.yaml', '/home/user/Desktop/enclosure.yaml')]


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



def _has_generated_python_file() -> bool:
    if not DESKTOP.exists():
        return False
    initial_python_names = {Path(rel).name for rel, _ in INIT_MAP if Path(rel).suffix.lower() == ".py"}
    allowed_names = {"eval.py"}
    allowed_names.update(initial_python_names)
    try:
        items = list(DESKTOP.iterdir())
    except Exception:
        return False
    for path in items:
        if path.name in allowed_names or path.name == "_runtime":
            continue
        try:
            if path.is_file() and path.suffix.lower() == ".py":
                return True
        except Exception:
            continue
    return False

def _run() -> bool:
    if _has_generated_python_file():
        return False

    import uuid

    runtime_base = Path(__file__).resolve().parent / "_runtime"
    runtime_base.mkdir(parents=True, exist_ok=True)
    root = runtime_base / ("engiworld_eval_" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    io_state = _push_utf8_text_io()
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
        _pop_utf8_text_io(io_state)
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("True" if _run() else "False")
