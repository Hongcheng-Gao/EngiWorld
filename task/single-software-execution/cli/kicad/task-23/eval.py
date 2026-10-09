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
