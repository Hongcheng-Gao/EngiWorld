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
INIT_MAP = [('board.kicad_pcb', '/home/user/Desktop/board.kicad_pcb'), ('spec.txt', '/home/user/Desktop/spec.txt')]


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
