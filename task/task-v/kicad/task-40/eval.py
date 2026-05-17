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
INIT_MAP = [('NO_TEAR.txt', '/home/user/Desktop/NO_TEAR.txt'), ('board.kicad_pcb', '/home/user/Desktop/board.kicad_pcb')]


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
