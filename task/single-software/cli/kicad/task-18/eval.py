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
INIT_MAP = [('ddr3.kicad_pcb', '/home/user/Desktop/ddr3.kicad_pcb')]


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
