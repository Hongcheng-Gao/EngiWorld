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
