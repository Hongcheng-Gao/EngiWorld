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
INIT_MAP = [('design.kicad_pcb', '/home/user/Desktop/design.kicad_pcb'), ('design.kicad_sch', '/home/user/Desktop/design.kicad_sch')]


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
