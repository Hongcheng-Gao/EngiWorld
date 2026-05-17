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
INIT_MAP = [('board.kicad_pcb', '/home/user/Desktop/board.kicad_pcb'), ('esd_map.csv', '/home/user/Desktop/esd_map.csv')]


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
