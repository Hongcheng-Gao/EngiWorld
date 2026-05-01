from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'common/__init__.py': 'eNoDAAAAAAE=', 'common/sexp.py': 'eNqtV0tv4zYQvhvwf5hqD5JaR9nt0akXKIpsD213F92iQBEHMi1RazYSpZJUEqPtf+8MSUcP27GzaA6OxHl9881wSAVB8IuQomIl6Av+2CiutaglNExprqCoFfwkfmA5FKLkGqLkTmQsT3W2gUvwL022hsvpxL/lqu1EVZ13L3pbxcl0Mp38qFhVMQVCA4OfhW5At2vNzXw6AfzTiAP/zRfATF3BPxBGoV38GsI4dDpWYnW0UUJ+Ri10v65LfJBtteaKAn2yMoyiOOR1uy75xV9tbXgOD8JsYLUMVsBkjg/LFXCdsYbrBD5ZR85qjT/TianvuETJe+vZSRQ3rZLoimkoypqZSyFNQumYfYWPW7Op5XRSWunDptYcGVXaAC95xaUhLsy2QZ7KcousuGSQrSAIppNCYbZpWrTokacpiKqplUHosjbMYL201yEXSIaXfy+3xMJ0kvPCVTQy/NHMibMYLt4CwfGkY5yPpIFOh53g+L3y6YDZcDB1c1Hye15aB4mFSD4aWEBqvSgbKPbLib4TTfqgI7/gXTWJxZRSMBINkKZIxDloScpZBXXRg9VPQJ/EV7cGBTe3R9A+bLD1cVnAd1ByGaFC7GF464Q1DZd5NEwo7nSOMYC2XdqFkLnNWtY5n8GGs9zl3uX8h+BlDpii2lo2jnYSFslvhxX5Wc0wYtYqLZCdbUeIKFBbSG2YzLiPS377+aEOCew+GSnfvL6dueqQ0K/AYuGwdy7ob2uhk063TtMlQ3bRsbSigza2sZ/IsfqOnbjPHTIwJm4GKGJtiS2EOwFL/L6WvMfmr11HOwZzgSwZD8nyi8kqQzvKzQvL5YA+3ICnKfTV9mjc+nO5D8viM7ZOLdHO7OnpOOc+rtUa9N0Tkh1/96xs+Uv5e4cprCJSh/vYtph1fn+FrYhd6Y07uiS6GBcq7pikxqUIgG5pn8kYN9y3J2j0a/Lmza3LJiuZ1rtd7o0pwzTFY86kaaR5Wcygmyy9ACRKNKIk6WhZ4PJrCrBzuNvRJO07cePC27iJ4fzGo+pk6NFJbpz27VCOnGSJ0Lph2ARj4x6ubxbwZijkJdlSU4RX4RzgFTYP8prVlR0QkbInG049zQoe7zs+noLtuiFo+ArDLGV4AOAJkJofsFnjNL/r89wbqWOqHZDhZPXM+bBvF88UQDGBbfo7tf61UrWKglZiHBwBeGhff3gX9Fw+V6wnsqPw8Aa0FqlLhLbxCKszDs4wdmdx3/yAEl2N3HH61Pu90GMOcbdwvCqMauqy2dsCwyoOz82ucX5T7biyxyr1gmodq5jhqhKSUc0oweCI92FucfiS/TQ+sfvrvePf2o9uAHtF8CU8vwzBqTKs2+JgGf6nEWRBLJcvJkw+mhPePfgdfX+HOETsKJlBaOyjoceAHgN6IhT299/kM8dT5NHMKEwcf9lsDL60CcIw+bMWMkLw8XlDrcsyOxfsiV53fRQcajE7APZmJd1kdgUR5/SKv9SNm7I7kmC5n8qB88FekZC0KN4j/GDi9mOr1zoEfL7XQK9wzGzpU48rkfWM1Xa+18NhEhIC5xhvFyEfvV937/OjVbcfeZFVig9Oavz+2xPzx4w3plfGw0PeQcGk6HvTX92nk/8AqENGEw==', 'eval_inner.py': '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', 'schema.py': 'eNqNVG1u00AQ/R8pdxjMH0eAW/HTUlAjFCQkBFXafyWyFnuWmm52rd0NIgqWOAQX6RU4Cidh9sOx06ShjiXH4zdv3ozfOEmS8Wj+nYkFmrWwYMpbXDH4++s32FsEY5msmK5Ao11rCXbTIHClgQkBSGlrZjFrNpSn68aabDxKHCPXagUVs6wUzBg0UK8apW0fegm8RlFFJNHW8msHmsnNeOR+Fzv4eOQv8PYWy7sgNR+PgA7JVpiTTh1uG1euyuGLUiJE8EeDpXUx4oUpfFQSwxNW2jUTh3GrBGomS+LlQjELP/3DPYxUNpSlqGs4RCvkUBQULYrUoOCTKNIdNEq7Ng5+Obu6SqDm4CBZUAwoDELybvb+Q9LnNExbl3LDk5ttIGiXsPV5rvE2WfbgjrBrGGrjZHrRAx073ow1Dcoq5UmXMd3uEbTJ5JA9DO3p3AEfmcPNM32UeTf2p5NTyvTP/XY//Si5f18nudLtDthOhhTR+gnQ+cJfsm+qlqnPnzzm1H6nYlnLzF1RVwOvGotNwWsx9G/pDG5yELWxNwO3L8kFfmNS8hijQMFpmEpvpg4Z1aLWSgdX7lkW4DlNwbphXF3PL4EzKlqRz4HsXXXmvWi0alDbTe/l4M1gZXj1Bmpp84PBmPUqLTsbu29DSbgw9dDN5EQFqywT/ykgUKZPpDOl0tjT+fXNj6yIGxTQGZ1DGmA6hfMHDon1z7Pzw6YHq3s2oBl+CWgwK6Y3vRx6MYMKopYYl/uavBHXOtqkzeN9qNGebfsabXRJfD0AqW877pj/n2evObl4+UjrD/r0SvpNAJgvFp8WnQKfsbdUx17yKUrqOy0nR1bqs4y75OEE+AcnCfRs'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('unrouted.kicad_pcb', '/home/user/Desktop/unrouted.kicad_pcb')]


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
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("true" if _run() else "false")
