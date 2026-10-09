from __future__ import annotations

import base64
import importlib.util
import os
import shutil
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
KICAD_CLI_PATH = "/usr/bin/kicad-cli"

BUNDLE = {'common/__init__.py': 'eNoDAAAAAAE=', 'common/native_kicad.py': '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', 'common/sexp.py': 'eNqtV0tv4zYQvhvwf5hqD5JaR9nt0akXKIpsD213F92iQBEHMi1RazYSpZJUEqPtf+8MSUcP27GzaA6OxHl9881wSAVB8IuQomIl6Av+2CiutaglNExprqCoFfwkfmA5FKLkGqLkTmQsT3W2gUvwL022hsvpxL/lqu1EVZ13L3pbxcl0Mp38qFhVMQVCA4OfhW5At2vNzXw6AfzTiAP/zRfATF3BPxBGoV38GsI4dDpWYnW0UUJ+Ri10v65LfJBtteaKAn2yMoyiOOR1uy75xV9tbXgOD8JsYLUMVsBkjg/LFXCdsYbrBD5ZR85qjT/TianvuETJe+vZSRQ3rZLoimkoypqZSyFNQumYfYWPW7Op5XRSWunDptYcGVXaAC95xaUhLsy2QZ7KcousuGSQrSAIppNCYbZpWrTokacpiKqplUHosjbMYL201yEXSIaXfy+3xMJ0kvPCVTQy/NHMibMYLt4CwfGkY5yPpIFOh53g+L3y6YDZcDB1c1Hye15aB4mFSD4aWEBqvSgbKPbLib4TTfqgI7/gXTWJxZRSMBINkKZIxDloScpZBXXRg9VPQJ/EV7cGBTe3R9A+bLD1cVnAd1ByGaFC7GF464Q1DZd5NEwo7nSOMYC2XdqFkLnNWtY5n8GGs9zl3uX8h+BlDpii2lo2jnYSFslvhxX5Wc0wYtYqLZCdbUeIKFBbSG2YzLiPS377+aEOCew+GSnfvL6dueqQ0K/AYuGwdy7ob2uhk063TtMlQ3bRsbSigza2sZ/IsfqOnbjPHTIwJm4GKGJtiS2EOwFL/L6WvMfmr11HOwZzgSwZD8nyi8kqQzvKzQvL5YA+3ICnKfTV9mjc+nO5D8viM7ZOLdHO7OnpOOc+rtUa9N0Tkh1/96xs+Uv5e4cprCJSh/vYtph1fn+FrYhd6Y07uiS6GBcq7pikxqUIgG5pn8kYN9y3J2j0a/Lmza3LJiuZ1rtd7o0pwzTFY86kaaR5Wcygmyy9ACRKNKIk6WhZ4PJrCrBzuNvRJO07cePC27iJ4fzGo+pk6NFJbpz27VCOnGSJ0Lph2ARj4x6ubxbwZijkJdlSU4RX4RzgFTYP8prVlR0QkbInG049zQoe7zs+noLtuiFo+ArDLGV4AOAJkJofsFnjNL/r89wbqWOqHZDhZPXM+bBvF88UQDGBbfo7tf61UrWKglZiHBwBeGhff3gX9Fw+V6wnsqPw8Aa0FqlLhLbxCKszDs4wdmdx3/yAEl2N3HH61Pu90GMOcbdwvCqMauqy2dsCwyoOz82ucX5T7biyxyr1gmodq5jhqhKSUc0oweCI92FucfiS/TQ+sfvrvePf2o9uAHtF8CU8vwzBqTKs2+JgGf6nEWRBLJcvJkw+mhPePfgdfX+HOETsKJlBaOyjoceAHgN6IhT299/kM8dT5NHMKEwcf9lsDL60CcIw+bMWMkLw8XlDrcsyOxfsiV53fRQcajE7APZmJd1kdgUR5/SKv9SNm7I7kmC5n8qB88FekZC0KN4j/GDi9mOr1zoEfL7XQK9wzGzpU48rkfWM1Xa+18NhEhIC5xhvFyEfvV937/OjVbcfeZFVig9Oavz+2xPzx4w3plfGw0PeQcGk6HvTX92nk/8AqENGEw==', 'eval_inner.py': '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', 'schema.py': 'eNqNVG1u00AQ/R8pdxjMH0eAW/HTUlAjFCQkBFXafyWyFnuWmm52rd0NIgqWOAQX6RU4Cidh9sOx06ShjiXH4zdv3ozfOEmS8Wj+nYkFmrWwYMpbXDH4++s32FsEY5msmK5Ao11rCXbTIHClgQkBSGlrZjFrNpSn68aabDxKHCPXagUVs6wUzBg0UK8apW0fegm8RlFFJNHW8msHmsnNeOR+Fzv4eOQv8PYWy7sgNR+PgA7JVpiTTh1uG1euyuGLUiJE8EeDpXUx4oUpfFQSwxNW2jUTh3GrBGomS+LlQjELP/3DPYxUNpSlqGs4RCvkUBQULYrUoOCTKNIdNEq7Ng5+Obu6SqDm4CBZUAwoDELybvb+Q9LnNExbl3LDk5ttIGiXsPV5rvE2WfbgjrBrGGrjZHrRAx073ow1Dcoq5UmXMd3uEbTJ5JA9DO3p3AEfmcPNM32UeTf2p5NTyvTP/XY//Si5f18nudLtDthOhhTR+gnQ+cJfsm+qlqnPnzzm1H6nYlnLzF1RVwOvGotNwWsx9G/pDG5yELWxNwO3L8kFfmNS8hijQMFpmEpvpg4Z1aLWSgdX7lkW4DlNwbphXF3PL4EzKlqRz4HsXXXmvWi0alDbTe/l4M1gZXj1Bmpp84PBmPUqLTsbu29DSbgw9dDN5EQFqywT/ykgUKZPpDOl0tjT+fXNj6yIGxTQGZ1DGmA6hfMHDon1z7Pzw6YHq3s2oBl+CWgwK6Y3vRx6MYMKopYYl/uavBHXOtqkzeN9qNGebfsabXRJfD0AqW877pj/n2evObl4+UjrD/r0SvpNAJgvFp8WnQKfsbdUx17yKUrqOy0nR1bqs4y75OEE+AcnCfRs'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('A.kicad_pcb', '/home/user/Desktop/A.kicad_pcb')]


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


def _call_inner(root: Path):
    module = _load_module(root)
    func = getattr(module, CALL_FUNC)
    args = [_resolve_arg(arg) for arg in CALL_ARGS]
    return func(*args)


def _apply_runtime_env() -> None:
    os.environ["KICAD_CLI"] = KICAD_CLI_PATH


def _run() -> bool:
    import uuid

    runtime_base = Path(__file__).resolve().parent / "_runtime"
    runtime_base.mkdir(parents=True, exist_ok=True)
    root = runtime_base / ("engiworld_eval_" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    try:
        _materialize_bundle(root)
        _apply_runtime_env()
        return _is_pass(_call_inner(root))
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    print("True" if _run() else "False")
