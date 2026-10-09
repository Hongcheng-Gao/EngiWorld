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
INIT_MAP = [('board.kicad_pcb', '/home/user/Desktop/board.kicad_pcb')]


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
