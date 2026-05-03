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
INIT_MAP = [('design.kicad_sch', '/home/user/Desktop/design.kicad_sch')]


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
    print("true" if _run() else "false")
