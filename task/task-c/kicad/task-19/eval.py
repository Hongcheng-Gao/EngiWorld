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
