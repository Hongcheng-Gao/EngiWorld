from __future__ import annotations

import base64
import importlib.util
import os
import shutil
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
KICAD_CLI_PATH = r"D:\kicad\bin\kicad-cli.exe"

BUNDLE = {'common/__init__.py': 'eNoDAAAAAAE=', 'common/native_kicad.py': 'eNqdWHtv47gR/1+fgqcUWCnraHeBFmi952td29kzzkmMPK5A46wiS5TNiywKJJXH5fLdO0NSLzvOBTWQ2OIM5z0/DpUKviFhmJaqFDQMCdsUXCgS5TlXkWI8l45j17isfgla/ZLrUrGsfiqXheAxlTVnWbLESVFHEal1xpaVgjk8Oo5zdTUdh+cTMgCZQcw3BcuoJz4sPNy4kB/d6+/uzUd34X/wndHZycnk9HKX3f2+kIdfXd+5+PVbeDm9nE12eBwCH7F0f1RMZfQnYCTTTbSiJBY0UjQhkSTB4T9//GTobs9soMH02+nZ+WQ0vJiQP/B5fHY5nM16ju+Mz6ezWTgeXu7X9v0rGOZpRpICgfzCRlECikgCSuH7j4N//QAsl8eLYISGQLzHQOkFh/5fGhtOrmaX09n0dIJq52cX4c+T4Xhyvl/twcEBOeZcFYLlihRcMp1JclS7y3N0F/j2qXGchKYkB5PuKfudhncsjpJQ0Ufl4b8+kUr0iKQ00T99cvQTfve1MNd1Rzy/p1gSkO+MpQx0auePMnZHCYogYBsnGY+SaFmHBgmBo4WMSiEomL+kebzeROIOciSpkoSniuYkYWlKBdG1Zcy0IjDQkmwilmdPZPlkLDoiaZlloDyn5PYrCYLglkDYNqBAWoYii2K65lkCUrEs0R2WryRR6wgaQlACLUHuo4wlmi4rV/U3SpaQjmutIuVCr4CPxiUJQVCax/MJS7Wopp6DTaTitYd0/0aLizMa5SDOXeRu8BtnuSZKPxBoVQFCPmqaYeZlrsDqAflsQoepE7TIvLCvE4vSr2HjTTdN+Ml5nvE4yiohNaES+nFAvtSL4H1JQQ92Z4D//qYbNTgdnkwu5sPRJLw6n/VI6j5jZbz0n62UF2jOSoagADU5ST/orcR91kKB44PjtOgWGQLAFA996ZmY7KtMzLonRayrEVoV8aVHEqm6C92CPeU5NaGAnSEiFPiGjCjJWAwSOgR47hKCB8EUNZ3RRPW1vql0BNCDdglKmydQZAO3VOnR313fWOj3aknbHIZSRQHczhOrI86Y180vze8r27kM4IkJngcrqjz3l+loOA5Hs6lNDJRkzR3lifG1WvED+sikgtLtb2exYjGpe1izeF2pNEdDoNc8V9t4BDY2ChvuHbENyam4wYM82kDxQVPkym22xGAvQzzV7Vcva2nuuL/QmhdLli9qG8Af6va2WEf9xVzwlYg25BghZKHhZPHlc/D5/9/9jz/ZfFP/QsioXUHcaPzqd3RBLHR2avpr6dmKZ83babFWUqp6MqUEWfUEnB/t3tGllbBYXRvkBzQx6paRpFV34CaT3zhdwaKmfSIuPBmoSngsW+v4aPFTg1BD0c+GVEqNbRUFH91KR7C5S5jwigiPCjm4FCXtER2OkN/pR7/W+15erfq9zGjNe3irhuz2YsyLJ8+vaNdVW56dHk+/hT+fnUzcG+wkJTzwdYdvfDa6whPkosuKvhreA/IfwAf+IMmyZFkiAdRzWWYKjjQKwaT3FFsN/hl5h4DvQuqjDg7aoFE3OxsNZ8P5HIadYa1Gh6ll05/Rry4m5/Pzs+PprDEVo9di6bjR0Bqsqco052IDB/HvNAmXT9AhnkaRDtLfgecN0msuU6/QBlFVrwbdNB4bOfigBwFv6S4EHLA9ssRztgYtFKsxSN6vWiBkhbYHUH1yvT1xwmh5MpxN/zsZN4OnFmVjkrUVJoJl2a7Kzhhqdb4hBYbBXRmdmdLKeNcM2ThAgL+j1iYNF6qsiTL3IrGSfZiNpMaRmx5mtb+FK3DUPyRVNvGMBhPxy5xu9R0jGMHcm1EwZW4W+m3FLT7UW7uMBrSP1/sB/DULoHkAf82CVAkv1aAlbj6dTzp0KsR+Op7zg+Mok7SlZE3ju/ZidZ7jJA/tFxbxMqSPeFEyhi95JJJwp8jN6FIuN0xBFMJIKJZGsdrlqZvBPBrR4XYuHB1gVUJQr5ecZ22Uhzn3nB6ZjSQi89G/SaWOPDA48M3wDROFnh+sI4akLZQSyseO9rctA2413kRFQfMEuyLFofO2PpluoQEpnI0UMcvEQV8lDTpdrukTDBq8zGBnhn38hBinYPgnkLWiVEdmpBGrUs/6UB2ZuSzA3SOC5GwKKD4RdGb5JtoWipoFfyvknZlxJxE1auC43920f6QyZQEztI5Zvmo2kibBz1vScDR6cR17d2Bg0s5o6Jhq3BShOagqs18fDSe/Dmfh5cl8PD2HtgYeoEFfeL5vBUHgBh1xn8BkOz7ARB8+13eEvwKqrunji1ttfO/ZqsRTv92p6FUzoKAFMA7Az87lQvLsXqdgpedB+K4h3X2GPS+uLmvc7vt66gIWnLdaNXnTQQsUAxHskcOO9F6rTpoNCAJoZ4V1vQpiGhuhHpArMPmG8Z6SH+Dq1h3eRPQAYjSfQRgCllaPUNr4uLT12oUifCcQPQQJRcledW0gQOFCDlwbDNcP7E3SeWVerGvQdLVt+zSCyTbB4tOKqnrDz4rmVOhTAXzHkx+uRPWauZxBwHvklbI1R3UnPI00JluXtH1GNuzPKOqlQSbsuxSuoEnLVFgv9ai5O0V0rds2DKJAY+viztbahlfcsRohyZWIt/3Z9iLhcLdBV/RrAvsepXHaAJ27jSOmrXalaSEg8C0xgB1RlrW6z17mxEYJalPJVhAEGtq6slOuOej3FkAIfd+vruJ1sLEK7Aul7tSGjHYEsLMbExA/BB4jCwCgK6YCXMO4H2QN3RRFFZCBPgorMwOxyvjS64r3a0S3m3YE2/XrzzeOPSrSlD3uHhFaWmCoQcYfqPD81oawMeq60ChV6HdJHdtS9/DZsL+4+q1SETBpYm1fI8FaRnOvK9PHQfDLjuVdptqBN0dQfH6Xqe5hkIhsj5UtSzsStw1t56/NV9tqiVgvzv8A7zsX1Q==', 'common/sexp.py': 'eNqtV0tv4zYQvhvwf5hqD5JaR9nt0akXKIpsD213F92iQBEHMi1RazYSpZJUEqPtf+8MSUcP27GzaA6OxHl9881wSAVB8IuQomIl6Av+2CiutaglNExprqCoFfwkfmA5FKLkGqLkTmQsT3W2gUvwL022hsvpxL/lqu1EVZ13L3pbxcl0Mp38qFhVMQVCA4OfhW5At2vNzXw6AfzTiAP/zRfATF3BPxBGoV38GsI4dDpWYnW0UUJ+Ri10v65LfJBtteaKAn2yMoyiOOR1uy75xV9tbXgOD8JsYLUMVsBkjg/LFXCdsYbrBD5ZR85qjT/TianvuETJe+vZSRQ3rZLoimkoypqZSyFNQumYfYWPW7Op5XRSWunDptYcGVXaAC95xaUhLsy2QZ7KcousuGSQrSAIppNCYbZpWrTokacpiKqplUHosjbMYL201yEXSIaXfy+3xMJ0kvPCVTQy/NHMibMYLt4CwfGkY5yPpIFOh53g+L3y6YDZcDB1c1Hye15aB4mFSD4aWEBqvSgbKPbLib4TTfqgI7/gXTWJxZRSMBINkKZIxDloScpZBXXRg9VPQJ/EV7cGBTe3R9A+bLD1cVnAd1ByGaFC7GF464Q1DZd5NEwo7nSOMYC2XdqFkLnNWtY5n8GGs9zl3uX8h+BlDpii2lo2jnYSFslvhxX5Wc0wYtYqLZCdbUeIKFBbSG2YzLiPS377+aEOCew+GSnfvL6dueqQ0K/AYuGwdy7ob2uhk063TtMlQ3bRsbSigza2sZ/IsfqOnbjPHTIwJm4GKGJtiS2EOwFL/L6WvMfmr11HOwZzgSwZD8nyi8kqQzvKzQvL5YA+3ICnKfTV9mjc+nO5D8viM7ZOLdHO7OnpOOc+rtUa9N0Tkh1/96xs+Uv5e4cprCJSh/vYtph1fn+FrYhd6Y07uiS6GBcq7pikxqUIgG5pn8kYN9y3J2j0a/Lmza3LJiuZ1rtd7o0pwzTFY86kaaR5Wcygmyy9ACRKNKIk6WhZ4PJrCrBzuNvRJO07cePC27iJ4fzGo+pk6NFJbpz27VCOnGSJ0Lph2ARj4x6ubxbwZijkJdlSU4RX4RzgFTYP8prVlR0QkbInG049zQoe7zs+noLtuiFo+ArDLGV4AOAJkJofsFnjNL/r89wbqWOqHZDhZPXM+bBvF88UQDGBbfo7tf61UrWKglZiHBwBeGhff3gX9Fw+V6wnsqPw8Aa0FqlLhLbxCKszDs4wdmdx3/yAEl2N3HH61Pu90GMOcbdwvCqMauqy2dsCwyoOz82ucX5T7biyxyr1gmodq5jhqhKSUc0oweCI92FucfiS/TQ+sfvrvePf2o9uAHtF8CU8vwzBqTKs2+JgGf6nEWRBLJcvJkw+mhPePfgdfX+HOETsKJlBaOyjoceAHgN6IhT299/kM8dT5NHMKEwcf9lsDL60CcIw+bMWMkLw8XlDrcsyOxfsiV53fRQcajE7APZmJd1kdgUR5/SKv9SNm7I7kmC5n8qB88FekZC0KN4j/GDi9mOr1zoEfL7XQK9wzGzpU48rkfWM1Xa+18NhEhIC5xhvFyEfvV937/OjVbcfeZFVig9Oavz+2xPzx4w3plfGw0PeQcGk6HvTX92nk/8AqENGEw==', 'eval_inner.py': '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', 'schema.py': 'eNqNVG1u00AQ/R8pdxjMH0eAW/HTUlAjFCQkBFXafyWyFnuWmm52rd0NIgqWOAQX6RU4Cidh9sOx06ShjiXH4zdv3ozfOEmS8Wj+nYkFmrWwYMpbXDH4++s32FsEY5msmK5Ao11rCXbTIHClgQkBSGlrZjFrNpSn68aabDxKHCPXagUVs6wUzBg0UK8apW0fegm8RlFFJNHW8msHmsnNeOR+Fzv4eOQv8PYWy7sgNR+PgA7JVpiTTh1uG1euyuGLUiJE8EeDpXUx4oUpfFQSwxNW2jUTh3GrBGomS+LlQjELP/3DPYxUNpSlqGs4RCvkUBQULYrUoOCTKNIdNEq7Ng5+Obu6SqDm4CBZUAwoDELybvb+Q9LnNExbl3LDk5ttIGiXsPV5rvE2WfbgjrBrGGrjZHrRAx073ow1Dcoq5UmXMd3uEbTJ5JA9DO3p3AEfmcPNM32UeTf2p5NTyvTP/XY//Si5f18nudLtDthOhhTR+gnQ+cJfsm+qlqnPnzzm1H6nYlnLzF1RVwOvGotNwWsx9G/pDG5yELWxNwO3L8kFfmNS8hijQMFpmEpvpg4Z1aLWSgdX7lkW4DlNwbphXF3PL4EzKlqRz4HsXXXmvWi0alDbTe/l4M1gZXj1Bmpp84PBmPUqLTsbu29DSbgw9dDN5EQFqywT/ykgUKZPpDOl0tjT+fXNj6yIGxTQGZ1DGmA6hfMHDon1z7Pzw6YHq3s2oBl+CWgwK6Y3vRx6MYMKopYYl/uavBHXOtqkzeN9qNGebfsabXRJfD0AqW877pj/n2evObl4+UjrD/r0SvpNAJgvFp8WnQKfsbdUx17yKUrqOy0nR1bqs4y75OEE+AcnCfRs'}
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
