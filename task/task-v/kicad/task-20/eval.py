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
