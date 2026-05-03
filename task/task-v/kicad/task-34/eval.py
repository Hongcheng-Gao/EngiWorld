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
INIT_MAP = [('design.kicad_sch', '/home/user/Desktop/design.kicad_sch'), ('pinmux_initial.csv', '/home/user/Desktop/pinmux_initial.csv')]


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
