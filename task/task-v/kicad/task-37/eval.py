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
INIT_MAP = [('design.kicad_pcb', '/home/user/Desktop/design.kicad_pcb')]


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
