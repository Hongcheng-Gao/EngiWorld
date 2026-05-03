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
INIT_MAP = [('board.kicad_pcb', '/home/user/Desktop/board.kicad_pcb'), ('board.kicad_pro', '/home/user/Desktop/board.kicad_pro'), ('netlist.csv', '/home/user/Desktop/netlist.csv'), ('stackup.txt', '/home/user/Desktop/stackup.txt')]


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
