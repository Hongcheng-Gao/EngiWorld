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
INIT_MAP = [('design.kicad_pcb', '/home/user/Desktop/design.kicad_pcb'), ('seed.txt', '/home/user/Desktop/seed.txt')]


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
