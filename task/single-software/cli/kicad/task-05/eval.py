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
INIT_MAP = [('design.kicad_pcb', '/home/user/Desktop/design.kicad_pcb'), ('thermal_model.csv', '/home/user/Desktop/thermal_model.csv')]


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
