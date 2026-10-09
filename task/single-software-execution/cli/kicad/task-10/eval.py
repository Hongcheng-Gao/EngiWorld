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
