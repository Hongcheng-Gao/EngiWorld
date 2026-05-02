from __future__ import annotations

import base64
import importlib.util
import os
import shutil
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
KICAD_CLI_PATH = r"D:\kicad\bin\kicad-cli.exe"

BUNDLE = {'common/__init__.py': 'eNoDAAAAAAE=', 'common/native_kicad.py': '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', 'common/sexp.py': 'eNqtV0tv4zYQvhvwf5hqD5JaR9nt0akXKIpsD213F92iQBEHMi1RazYSpZJUEqPtf+8MSUcP27GzaA6OxHl9881wSAVB8IuQomIl6Av+2CiutaglNExprqCoFfwkfmA5FKLkGqLkTmQsT3W2gUvwL022hsvpxL/lqu1EVZ13L3pbxcl0Mp38qFhVMQVCA4OfhW5At2vNzXw6AfzTiAP/zRfATF3BPxBGoV38GsI4dDpWYnW0UUJ+Ri10v65LfJBtteaKAn2yMoyiOOR1uy75xV9tbXgOD8JsYLUMVsBkjg/LFXCdsYbrBD5ZR85qjT/TianvuETJe+vZSRQ3rZLoimkoypqZSyFNQumYfYWPW7Op5XRSWunDptYcGVXaAC95xaUhLsy2QZ7KcousuGSQrSAIppNCYbZpWrTokacpiKqplUHosjbMYL201yEXSIaXfy+3xMJ0kvPCVTQy/NHMibMYLt4CwfGkY5yPpIFOh53g+L3y6YDZcDB1c1Hye15aB4mFSD4aWEBqvSgbKPbLib4TTfqgI7/gXTWJxZRSMBINkKZIxDloScpZBXXRg9VPQJ/EV7cGBTe3R9A+bLD1cVnAd1ByGaFC7GF464Q1DZd5NEwo7nSOMYC2XdqFkLnNWtY5n8GGs9zl3uX8h+BlDpii2lo2jnYSFslvhxX5Wc0wYtYqLZCdbUeIKFBbSG2YzLiPS377+aEOCew+GSnfvL6dueqQ0K/AYuGwdy7ob2uhk063TtMlQ3bRsbSigza2sZ/IsfqOnbjPHTIwJm4GKGJtiS2EOwFL/L6WvMfmr11HOwZzgSwZD8nyi8kqQzvKzQvL5YA+3ICnKfTV9mjc+nO5D8viM7ZOLdHO7OnpOOc+rtUa9N0Tkh1/96xs+Uv5e4cprCJSh/vYtph1fn+FrYhd6Y07uiS6GBcq7pikxqUIgG5pn8kYN9y3J2j0a/Lmza3LJiuZ1rtd7o0pwzTFY86kaaR5Wcygmyy9ACRKNKIk6WhZ4PJrCrBzuNvRJO07cePC27iJ4fzGo+pk6NFJbpz27VCOnGSJ0Lph2ARj4x6ubxbwZijkJdlSU4RX4RzgFTYP8prVlR0QkbInG049zQoe7zs+noLtuiFo+ArDLGV4AOAJkJofsFnjNL/r89wbqWOqHZDhZPXM+bBvF88UQDGBbfo7tf61UrWKglZiHBwBeGhff3gX9Fw+V6wnsqPw8Aa0FqlLhLbxCKszDs4wdmdx3/yAEl2N3HH61Pu90GMOcbdwvCqMauqy2dsCwyoOz82ucX5T7biyxyr1gmodq5jhqhKSUc0oweCI92FucfiS/TQ+sfvrvePf2o9uAHtF8CU8vwzBqTKs2+JgGf6nEWRBLJcvJkw+mhPePfgdfX+HOETsKJlBaOyjoceAHgN6IhT299/kM8dT5NHMKEwcf9lsDL60CcIw+bMWMkLw8XlDrcsyOxfsiV53fRQcajE7APZmJd1kdgUR5/SKv9SNm7I7kmC5n8qB88FekZC0KN4j/GDi9mOr1zoEfL7XQK9wzGzpU48rkfWM1Xa+18NhEhIC5xhvFyEfvV937/OjVbcfeZFVig9Oavz+2xPzx4w3plfGw0PeQcGk6HvTX92nk/8AqENGEw==', 'eval_inner.py': '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', 'schema.py': 'eNqNVG1u00AQ/R8pdxjMH0eAW/HTUlAjFCQkBFXafyWyFnuWmm52rd0NIgqWOAQX6RU4Cidh9sOx06ShjiXH4zdv3ozfOEmS8Wj+nYkFmrWwYMpbXDH4++s32FsEY5msmK5Ao11rCXbTIHClgQkBSGlrZjFrNpSn68aabDxKHCPXagUVs6wUzBg0UK8apW0fegm8RlFFJNHW8msHmsnNeOR+Fzv4eOQv8PYWy7sgNR+PgA7JVpiTTh1uG1euyuGLUiJE8EeDpXUx4oUpfFQSwxNW2jUTh3GrBGomS+LlQjELP/3DPYxUNpSlqGs4RCvkUBQULYrUoOCTKNIdNEq7Ng5+Obu6SqDm4CBZUAwoDELybvb+Q9LnNExbl3LDk5ttIGiXsPV5rvE2WfbgjrBrGGrjZHrRAx073ow1Dcoq5UmXMd3uEbTJ5JA9DO3p3AEfmcPNM32UeTf2p5NTyvTP/XY//Si5f18nudLtDthOhhTR+gnQ+cJfsm+qlqnPnzzm1H6nYlnLzF1RVwOvGotNwWsx9G/pDG5yELWxNwO3L8kFfmNS8hijQMFpmEpvpg4Z1aLWSgdX7lkW4DlNwbphXF3PL4EzKlqRz4HsXXXmvWi0alDbTe/l4M1gZXj1Bmpp84PBmPUqLTsbu29DSbgw9dDN5EQFqywT/ykgUKZPpDOl0tjT+fXNj6yIGxTQGZ1DGmA6hfMHDon1z7Pzw6YHq3s2oBl+CWgwK6Y3vRx6MYMKopYYl/uavBHXOtqkzeN9qNGebfsabXRJfD0AqW877pj/n2evObl4+UjrD/r0SvpNAJgvFp8WnQKfsbdUx17yKUrqOy0nR1bqs4y75OEE+AcnCfRs'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('mipi.kicad_pcb', '/home/user/Desktop/mipi.kicad_pcb')]


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
    print("true" if _run() else "false")
