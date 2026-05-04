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
INIT_MAP = [('board.kicad_pcb', '/home/user/Desktop/board.kicad_pcb')]


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
