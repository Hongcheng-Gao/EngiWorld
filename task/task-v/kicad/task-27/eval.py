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
INIT_MAP = [('power.kicad_sch', '/home/user/Desktop/power.kicad_sch')]


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
