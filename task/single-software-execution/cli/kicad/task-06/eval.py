from __future__ import annotations

import base64
import importlib.util
import os
import shutil
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
KICAD_CLI_PATH = "/usr/bin/kicad-cli"

BUNDLE = {'common/__init__.py': 'eNoDAAAAAAE=', 'common/native_kicad.py': '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', 'common/sexp.py': 'eNqtV0tv4zYQvhvwf5hqD5JaR9nt0akXKIpsD213F92iQBEHMi1RazYSpZJUEqPtf+8MSUcP27GzaA6OxHl9881wSAVB8IuQomIl6Av+2CiutaglNExprqCoFfwkfmA5FKLkGqLkTmQsT3W2gUvwL022hsvpxL/lqu1EVZ13L3pbxcl0Mp38qFhVMQVCA4OfhW5At2vNzXw6AfzTiAP/zRfATF3BPxBGoV38GsI4dDpWYnW0UUJ+Ri10v65LfJBtteaKAn2yMoyiOOR1uy75xV9tbXgOD8JsYLUMVsBkjg/LFXCdsYbrBD5ZR85qjT/TianvuETJe+vZSRQ3rZLoimkoypqZSyFNQumYfYWPW7Op5XRSWunDptYcGVXaAC95xaUhLsy2QZ7KcousuGSQrSAIppNCYbZpWrTokacpiKqplUHosjbMYL201yEXSIaXfy+3xMJ0kvPCVTQy/NHMibMYLt4CwfGkY5yPpIFOh53g+L3y6YDZcDB1c1Hye15aB4mFSD4aWEBqvSgbKPbLib4TTfqgI7/gXTWJxZRSMBINkKZIxDloScpZBXXRg9VPQJ/EV7cGBTe3R9A+bLD1cVnAd1ByGaFC7GF464Q1DZd5NEwo7nSOMYC2XdqFkLnNWtY5n8GGs9zl3uX8h+BlDpii2lo2jnYSFslvhxX5Wc0wYtYqLZCdbUeIKFBbSG2YzLiPS377+aEOCew+GSnfvL6dueqQ0K/AYuGwdy7ob2uhk063TtMlQ3bRsbSigza2sZ/IsfqOnbjPHTIwJm4GKGJtiS2EOwFL/L6WvMfmr11HOwZzgSwZD8nyi8kqQzvKzQvL5YA+3ICnKfTV9mjc+nO5D8viM7ZOLdHO7OnpOOc+rtUa9N0Tkh1/96xs+Uv5e4cprCJSh/vYtph1fn+FrYhd6Y07uiS6GBcq7pikxqUIgG5pn8kYN9y3J2j0a/Lmza3LJiuZ1rtd7o0pwzTFY86kaaR5Wcygmyy9ACRKNKIk6WhZ4PJrCrBzuNvRJO07cePC27iJ4fzGo+pk6NFJbpz27VCOnGSJ0Lph2ARj4x6ubxbwZijkJdlSU4RX4RzgFTYP8prVlR0QkbInG049zQoe7zs+noLtuiFo+ArDLGV4AOAJkJofsFnjNL/r89wbqWOqHZDhZPXM+bBvF88UQDGBbfo7tf61UrWKglZiHBwBeGhff3gX9Fw+V6wnsqPw8Aa0FqlLhLbxCKszDs4wdmdx3/yAEl2N3HH61Pu90GMOcbdwvCqMauqy2dsCwyoOz82ucX5T7biyxyr1gmodq5jhqhKSUc0oweCI92FucfiS/TQ+sfvrvePf2o9uAHtF8CU8vwzBqTKs2+JgGf6nEWRBLJcvJkw+mhPePfgdfX+HOETsKJlBaOyjoceAHgN6IhT299/kM8dT5NHMKEwcf9lsDL60CcIw+bMWMkLw8XlDrcsyOxfsiV53fRQcajE7APZmJd1kdgUR5/SKv9SNm7I7kmC5n8qB88FekZC0KN4j/GDi9mOr1zoEfL7XQK9wzGzpU48rkfWM1Xa+18NhEhIC5xhvFyEfvV937/OjVbcfeZFVig9Oavz+2xPzx4w3plfGw0PeQcGk6HvTX92nk/8AqENGEw==', 'eval_inner.py': 'eNrNGl2P2zby3b9iTgUOUiKrtjebtEZUIJem7SLJdpEEdwUMQ6Al2uatRGlJemN3u//9MCQlUZK92eTu4fKQlcnhcGY4X5yh53lvbkm+I6oUsC4FXLOUZOMfwP/w6cPkDMZjeH9xdQGMK0HGFWECcso3agsFUemW8U0QjUavtzS9lvPRNAL4heUUKiIklUAk3JKcZQZrUqWr0Wz8PIJfSgGUpFso16C2FM7NJohehvDXu+QKxvAuufwLXsbw4nxXjF5EAK/yHK6+vwRJNwXlCjhVEuieSTX6AacV5JRIBedAsowpVnKS18ASfElFRbliHAnLMpoFox8jgMsScnKgAtIt4RsKPslzQ06zVCpygJLDL9HrXTCaTiL42OBqobbklkKaUyIITyn8FMMkmk6KAtaiLIBk/yappbpZMwIA8CUrqpytGc3mkKIkoWAcMiaVRrSi6jOlXNOU/JFcAeFZ/aMVBuVZVTKko9k4GE2nkZZaKdiGoTQuQQmSogAEhR03LGfg2zOViuU5nE2is6KAp9+PG0Se5400G0my3qmdoEkCrKhKoYBwXiqC0pYjO1Q2X/LQfBZEbQ2OtMxzmuoVNZLX5Y4rKkLI6JrscpWxVOGPmx0djeRBRhVR24hxSYXyJyGUduTfJeN+/SNjgpOC+kmyZjlNkiAEL4q8IDDbynRLC9LsiIL+QOUuVyGgCZjvmsKiKHkk6b6q4bVGh7BmPEtInuOXkF1wThS7pYnW9XpZWhYVERRVP6F7HBqNPr36+Da5+Bli8Ky1eaPf3nx4AzGcZGX05o+r3z98Si5fvUc4b53uInm78erxtxeXGqE79urDrx8hhoXWMq9KV14IniECvxA0NHPjcVFmdCwZ3+S0GcwRCnW+BaP7NN9ldJwJ8pnxzVhuKVXtdEU2iOVPqvHh8lkzWeLPO1VU99/XxIej5Wh09erig2arpdX3tHq/fvc2ucJVza9LLwhdiJ8nGgCaXwOAaQdgOgSYdQBmQ4CzDsCZAViOLpPfP1z8enH56l3y7s3lr59+S96/h1jbzujj2zf/St5dvL/4ZAYn0eTFOcB3xpWNRhldo90mjK9LX9JNMNc7SkWEgthoFo7jIeGYF+h5yrPeLOWZnfvMMrXtzeoxO29cXHdej9l59ErdWU7rfQVVO8HB1z/w3zovifI1aYvpMgg7A7N2gPLMncefONvDo8lEOGBrywfNJUWptaBSCV/TWwMahjSg57VwjCufU1VDIVsGmQEJrPR5KQqSsz9plki24QRdmnMS+2kIh2kI+1kIh1loqArNnqGVVecA6/OxLjgGWQpFM9/3RbnjmY8InwchmF8H/SsIoZ6ddWb1ryDoCr9Bvpgsw3arxXRZr7NEIqKW0KBVNwwTSR1VfBLCynJLkDqCRBGkhCABTxKXRWJoWSHgCgFXCLgaAq6CkYbELUvBKDeRwa/2IVSHEG72IdwcQhD7EMTB7u+yebOHMVT7AJ6ALw74fQhgDP5N/Y3jFsbZiieWwcfvVDBDltjjBlM6/hGTjZs9/l+QfTP31MwRnjUo6n8axUHjd1EcGhR2zqBw6GUY7CRNlfQdysopRgBHascOpj6DoF02e9Qyc2DOsrPesmOnW6Nylj171DKzb7uMrZG9J0jsSxhP6Xg603lMeYaDz5rBeUfI9qw+iR0dnF8H0Ccr6ZfTACXvIG/VopVJS29DZQClOIJu9jh0A6ZPoDs7jc6lqY/4FLpnj0M3UID2TByF1M4kUeXAjLqe0FHWbB9CdoAY9jMYGzD8OEzdI8/2EMcw0fQhcAyToweMuWG0PVQlbmzRVQeNriUXnS5aFcYFbXpT/PDrFegasj08Bb9eiQOHAL4HP9vXk9nBjDpiOEGDv5/CU1B6YWDJ8Q/N2CGw4mOnzNninUQT15Ej4Q3IQOzH1LQ5ufChdX3/8Lh1xxSv0eMH1/U9xGBdHXm2RCaY02KclCHIcidSGoIiYkOVFddGkAqzFyf79yUGL50llAIDDDCOf2Qr4H6U7oaiJizrEBfCCmL49mjcYNKkLsgyIlmG4a47vjLjNl7e7OiOarZudtRfGNaXZu6WSaYoJnR3Zvze5HFbvD7rhfOu+CE2w1FVVjldK7/jXC1IbOX6ZTeKUuWUbbarUqBoDf0azRLGNXldPHZQs1ivDToQhkJSVZT3QSwRv5BcUicHNjdPfVow/smkhP99OoypX6nApKTa/VCefdk20QXIG6F8v5PAwrif8gbw5AnM0Nl0Utse4KwGrG2BmlIL9dEg5pjUhmAuZEkzAn/BZclRbfCPFkp7PTUcYCLfjvmKyOuEZbG9V4YgFa30xTFGrB2J1BdMXTaRmg5XLBEVotT3BA/X6yVrtIM53CHsvdcXoQlNShxaLJ+Z2kJZUW7QYxVo3VUkRff6ZCNBSeYocpWileqrto8w9qD3Ka0UvNF/WMkRIT1OtF4K+vcc7ugxcvXIdzAej00NAKb4beQa6fKLrBXYqRG0Phvv5bGny1pJU9ZybiAVkZJmsc8k4zbXrtJVCDmTKtCqiFzav4vJEo3WaxE5XpfuK5oqmsXOdAgkVTuSx3YxRp8HN9K3H9Qk65WDWgD/2LE803cZ5AjVjO+KFRVQkKq+EiY4hX6f7wr0VPftxK7Q47i0mdA+BZ1JXSUxBJmr5Nx1VznlPg+wVHXW1Yzepgu+mC2XEJt7HVreELqlZNFA4RJc2mW2KdWtDg3jxtXQjUxWh8Tc7BxubNzp8WPxuDxpSsqMnrxE1zZYwzGpT6XLfVpiTdHx0pzXvNt1HRFwK/6eGKINVT7nob40c+4EL4fPSFJlw62v8YSwWAa15uvgOeoac6fmhvWqEDzGmdKeBss0BatY5Ghy3/I1sGvitf1bD4XTPb3q3uuR+bnhSnvbob7VW9Si7+maRnff7vboc3fw/g8Ov3vofUrck+nLRB9tXx9C8LzgxPE5jk7CbPx87lby5TX9DBUVuvDeeEHkvzIaYRSMcWiLdE5Wook2KVdDO9JXNerUSugULB/CVpgTIOiu8N0MwZy3RHLM1i76Ly7hvSWa9xjwKmU2HBsszr3gMdGgiQhrDzEmd5r5xfzF8j7JaYIFPyc2uPFBE/Ayhm6xUJcKngfdJW0geBkfwWgjwtq7Q5xPppPJZB5N1/cDQFXmVDcn4s6mLVAw1Bp4MQdiGy9tw8UYR04bpSF5nuhpPGKrnq0bj67pQfpNRetmxwTNavg7blQOdbCjaq1949z914ZoJAldkt4n0WQPw3SHmIhJuVsh/TU7x6KxLe11Vjpw9jQsVCOXv8OxBccE/sMcVKna1hWk2ByBn2A6Af/cNMngCVyOtUk9BVkWFK7AaW8FnWOxlodpgX8qkAWWit/rRtGWSNyv7Z7NGkcRRPCKy89U1EBP4dmT8/hsAnSvBNEmro/u6mtPzGEh0R264Xkh7ejQT/ucAH7SLn/gVntgg2pe1/UlXV08mpbpFuaVaalpYRSlcBqCaks4MCXb9ptUgrDNVuHdUlFvoDTGe8zhSxyepvO+q1dVkpacY7PtlqlDUl5D3F4DT2NxapI16TF8QaD99K5eGcDfYph2Q94xsszF8MFs6OELf73hYtIlBu8wnSLEcfrDYwph6m0PVQ2+uOpobf9rxPEVBlQlWheTWhRJ0yeodzhmU4PtH9B1rbggaEEYl9AgbZrUHXVvdh9quldee7puMWDdtHQyJlvk+Fqg6a3YnrV32oH+OAf+UFNfNr38xk9q4CPmYfPA2o3+n+f7Xm9vPalLERLTeNvR9HraZ3g/wozbH3SNu4XHS2b7czFdoq2blvF8YBiOjL9JuXmZGBTmTId6XG9wTH2HjzqsDpxWzYZeo5Edfcqoco3pmBZOJ3NQYkchLauKijHNNu7zkNpg6C0VB5P8lOvuw5DvkMaMrddUYBqgyddpCnzaMgkpPsChElJRSuzcS30cnBIBpKpESfQs4/jCxuIrWJbl1N0oNFUhnh8aE4NKlHtWMHWIRrbLlWi6dSfb1PcbPno2047fsjI3r0Kwrb+0mCqWNAdQd/u1szRuWFcBddZX/5R12bd22kzRQvqmuXtCvfsVY73LsrFpxjO6D82WCdG7JCRAYMp3BRVYn+tQ6thLTVuyMutWuKwDvNDoMY+fL+d90zFbYsXHIBkaycAjmBviukRK9d9Vr8idkCDsDqwGJmsQLM61fRosi/PlI3dHxU1axY2HvWRNhRWI7tba/Z4t4Wm93bMldmJmtuDq0NZD/9LRN91TfX6EzK72DTOHU6pYe5nm7OuzNNG5S4qJ1KNvT2ITl86hu3Jnj7istYevwNz3ZHeNZO6L4rTf6khH+65joljMz5cPOK/pvH0rVgkqqbil+qkePmjKqaJtlN/QsqBKHKImmvKkfVoWY/BsZWQfevknH2D0jfd4saDV8Dj+OpxHs9hjiHFNcrQEYttbXxu+TG4mW9kMVcIR3Kkg1r74q+Vun6dI++xDhjYOKLj4Ga/rJFX5oTnE7LTiuMdmYp5VAe0X9E30aO6FRtw2MYaZjjsZP/x0TzcMQnAeu9UtAI2ivG76JbxU6IuG7+taua9KIjK9re6DOI+JdquCKUWzhAjF1iRVsUNjC3fNeBY7D+zCPktEbGTsvLYLv1E1zMNBebuxPCSFie2JZmGoJ604jmiJfV3XnLzFBW/Za5LB63cXOu+Bj//81bJhHqiicTeCgf7GVlUc4Xd1oG2vNI2upNypaqekb/4mGROmwRWDF3m6sYWNXqMnR5WjWXekuDz6kmY5iwfqhDR0enGdNlynX9mWoD3bZ/PmICL7jTWUtBRUj+mvEDxzSHrIfIYODqzsGAz4hU1LbFbpEf3lwBr98eZOnoT/7jzUGm8OaWTcVrthWm+o33maDBVH6x+926pnTlWDmM8QKbRFQj3c/MLLTanstqWy7WrXWaboJWutb2aXDkNyVxREHIywzLdvb9D3o9GIrSExVcNEN8WSBG+ZSeJ1VARfAxOxucXbhi011ENY+pla19XTlyPq0iCaHUU0M4i+yV1VAu9wD2hYy34w+g9YehFZ', 'schema.py': 'eNqNVG1u00AQ/R8pdxjMH0eAW/HTUlAjFCQkBFXafyWyFnuWmm52rd0NIgqWOAQX6RU4Cidh9sOx06ShjiXH4zdv3ozfOEmS8Wj+nYkFmrWwYMpbXDH4++s32FsEY5msmK5Ao11rCXbTIHClgQkBSGlrZjFrNpSn68aabDxKHCPXagUVs6wUzBg0UK8apW0fegm8RlFFJNHW8msHmsnNeOR+Fzv4eOQv8PYWy7sgNR+PgA7JVpiTTh1uG1euyuGLUiJE8EeDpXUx4oUpfFQSwxNW2jUTh3GrBGomS+LlQjELP/3DPYxUNpSlqGs4RCvkUBQULYrUoOCTKNIdNEq7Ng5+Obu6SqDm4CBZUAwoDELybvb+Q9LnNExbl3LDk5ttIGiXsPV5rvE2WfbgjrBrGGrjZHrRAx073ow1Dcoq5UmXMd3uEbTJ5JA9DO3p3AEfmcPNM32UeTf2p5NTyvTP/XY//Si5f18nudLtDthOhhTR+gnQ+cJfsm+qlqnPnzzm1H6nYlnLzF1RVwOvGotNwWsx9G/pDG5yELWxNwO3L8kFfmNS8hijQMFpmEpvpg4Z1aLWSgdX7lkW4DlNwbphXF3PL4EzKlqRz4HsXXXmvWi0alDbTe/l4M1gZXj1Bmpp84PBmPUqLTsbu29DSbgw9dDN5EQFqywT/ykgUKZPpDOl0tjT+fXNj6yIGxTQGZ1DGmA6hfMHDon1z7Pzw6YHq3s2oBl+CWgwK6Y3vRx6MYMKopYYl/uavBHXOtqkzeN9qNGebfsabXRJfD0AqW877pj/n2evObl4+UjrD/r0SvpNAJgvFp8WnQKfsbdUx17yKUrqOy0nR1bqs4y75OEE+AcnCfRs'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('mipi.kicad_pcb', '/home/user/Desktop/mipi.kicad_pcb')]


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
