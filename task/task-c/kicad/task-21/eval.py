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
INIT_MAP = [('board.kicad_dru', '/home/user/Desktop/board.kicad_dru'), ('board.kicad_pcb', '/home/user/Desktop/board.kicad_pcb')]


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
