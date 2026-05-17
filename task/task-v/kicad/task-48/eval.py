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
INIT_MAP = [('analog_region.yaml', '/home/user/Desktop/analog_region.yaml'), ('board.kicad_pcb', '/home/user/Desktop/board.kicad_pcb')]


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
