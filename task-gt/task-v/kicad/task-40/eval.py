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
