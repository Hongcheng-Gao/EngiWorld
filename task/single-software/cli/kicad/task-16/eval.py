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
INIT_MAP = [('board.kicad_pcb', '/home/user/Desktop/board.kicad_pcb'), ('slots.csv', '/home/user/Desktop/slots.csv')]


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
