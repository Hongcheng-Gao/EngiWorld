from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\Administrator\Desktop')
BUNDLE = {'_shared/build_native_task.py': 'eNqVU0tPhDAQvpPwHyacIOKaeDKb4M09Gg/e1DSVDmxdaMl0quu/t+W1ajysPRCmfI/5pqUh24MQjWdPKATofrDEII2xLFlb49IkTebdN2fNWri9Z92lSRMVBsn7Tr8u9IdQRl6aKGyA0CELlu4glCaXL2/bEVfA5S2wHzp8imU5br5s0wTC0kZzhEIFCwuuIBu3G91hNsHav0AtWW+UYPK8n3G6WRU3eNSOXV7MTnFNkTbUMyHmC7JYue2ZzPYHbzHsD+GZD5LQsKseyWMJo5Swh7Esvoc5G04Yjs6sNuXMP42/tsOnMOEw33GcWe6spxqn6Zeg0PG3k7i3Brdr4nALYIL/lZqkdgi7oHlveRenfUdkaTaY+4v6mynG2ZnmccbOr2e1qdHiFOuDNKPA44A1oxLxbubxGq65JMstKF3z71wR9d+ORs5kyXjk/DSEaLxRvh9cHi3LcBIqiFXXQci4+FdJV2td7WTnsIALyJ5NVp74aGqrtGmrzHNzebN8Cr5fqAUoRg==', '_shared/native_altium.py': 'eNrVWFtv2zYUfg+Q/6DxSUpcI277sAXQCjdxi2CpUzjpsM32BFqiHC0yJVBU4iDOf985JCVRshOvGPYwA4FNniu/c+FhYpGtnCCIS1kKFgROssozIR3KeSapTDJeHB4cHpjdv4qM1wvBDg9ilM6pvE2TRSX6FZaGIh/zhC8rwoVkgi5ShgqvLkfBl+HnizPHdxZktj4/ma3PPs3Wg8FsPYLfQ/j+CH+DIawHBEUODyIWO4wX6CgH3+5ZkKXMRfOnyqrnvPnZGWecnR4eOPCJqKSgHxn6gtEoWDxKVriepiaxA2dUTP1CUiGLh0TeurVnntGCH0GTgjm/0rRkIyEy4cbkSanldMWenaRQqih3hqlMypUDSpwwg2OXPHKiLCxXjEviNcdQ7qRwCD7oHqCQwlgWDILCt/3vRyzMIuYSrYD0HIZOFT5JljwTzDaUU1GwIE9yFsQJS6PCLdgSvTlFQ8pglIRyCose7syN7awEjjYFoHx61tQ4E6hZOgl3jL5+kaeJdMmG2MAByMQnCp2EKxGLiJ8w43CGkjW7dz3nXkVN1Dp9OOLAa1jAuekd+nPfAgq2rURZS0FDGRThbaBCwcHJogt2mhRyiseszr07v4xtCUrBajd4hrpIs/CuUPR+nPAogXx3rRwis81kdHY1OfcHs03/6IP7wbd3NvXi3U+4+sMjvUYaTVvLOKXLwgdD12bT+NCc9NQ6G/g0nTeRW1EZ3mI8tMdWRNQGcCuO/lJkZe6eWMDrFNLR6aSVErVYI1ZANlIJ9nxVlA3pHutoaxdcxzza2le5Jlborw2sBed7jedscwMg+e70z838yJttxlCbenUMK0gh7WInARHYQHnUc7Ca8XBiZc4+8HrW6q3XFsUOoiR8h6jeQDq67cM2dto8LLXVnGkQdilq8NmlCuAOVjr3CkZFeGsD9O79FkDHFUDndZwsjFoFrFR3HGpFVzHUiLUiqpMRO0dbnsCFIVhMTk1K9ZcM6vwyWUxYzATjITSxXkeksQlizaLLdq8joYHvEsMK3wrOLsMaSIHMgoRLt+VaFqrrsP8b8bY8e9wn9PsOISghwB9SuQDpp+cuWdCHQAUDqOrbYnj+P1RHHf2pfdT5FNXMX8jipn31aZ4zHrn1jtdq9Q1j0/Gx0y8egyYzus2+uc7sjt+56aqGaV91aA0RfuVOsYFrFQfy6Wyw8nerwAyhgz7ecw1xbrTtv/PycBEoeM3dvPvas277f3HrGT+mYEphhd8AFQpV1/dsfXJCPDULbIgZGea7vRZlyl6+pJtZpHJc8Z/u5Ohcesav1yHqji6Tb5ejXy7G580IA+x7JxjlVJXAOwcwrw2eEtgNyD8YXbZRQaH/EJXrq2+Ts9H56Pri83h4czVpoeOAVvJ1eHMzmoy/Dzbl9ffApgR2w7bIqIgqyRfbgFUBrye5VrRnIK7Hqhca8Uf0abZRPRcasmfPf4ampz497Fkznh0Ac7+UOTxc2A6YsMSOWwPcwOvgpjkb4NBZEBeFVPVn4dVzjnoqO++ARb0Y9DWgfjobNamZgW0HtIbBKlVUE6TZA8POWG301Ub1LEP1NQsuKnI9brEU3mLNjIjQo6puHjetpJO/SNAduSpvgJwQrzb0g99xdm/qGteM3+Y5qMCh8ABsDI6HX0bbxhrR/a2laRitkGo4WgGlabrVTrfjua+VIOOLsap6v9BBeCUCCvdXQYfpFw1Y9wIMVPgPh5b7+FrXZdh97KtX8oOAolMdzEXRflRCh3BRqAfORdDR/Le96rajRZgk/icK6eRByZAZx5c0h6d1wpc+KWX85kf7KV1NeGpmsStAuQKUdr7DifXsD+lgbW8FTXUf8bhNrm0ZtNk6ZLm0/gvxksa/AR3nVXA=', 'eval_inner.py': 'eNqtV1tv2zYUftev4LiHSoOjNl0fBmPeECRpG2CJgzRFH7JAoCXKZiuRKknlgjT/fYc3SbZsdxuqF0nkOd+5Hx6WUtQoy8pWt5JmGWJ1I6RGhHOhiWaCqyjya5+V4OFb0vClHlVUGpCG6FXFFgHhEn6j6P3p1Sma2Z8YpLAKZCSppEpUdzRO0oZIynUEIKnhTxlXVOr41QQpLWPD7UnQS4QztYLvAidJ5ERy0PCOZqTSrK2DYMqVMcXviYpOQFtSZBUs8EOEfkZcfCVTdPrm1esoigpaokzSry0DJsFzGmv6oKdG/sTYpKnk/q+gKrefCTr4w7zRN3QhOJ1GCJ6a6HxFFVgraVoyXpCqij3ABBnQCSorslQz2P+QWB5Woory2LMm6KcZOnRo5pEUgsJRiZ+M5GeUixYcUTNl6aeIPjQ017SAD5Lr6hEdTtBSaPQ0xHzG0QDLqOuNpnekykSrm1ar2L2zgjnbCpZrp0e/EcI4IO0DaWkJV5mJIlAO2CBw96xksMNplV7mixORO52WOpDbNAHCpQQTi0zLVq+wWQgmpib5giU2zDP0hBuiFJ6it6RSEGXcC8U2TENVn6PgcEjsTtOUPjAF5idDpxv4Gww5Y0TegqCyU8PbhUwim0AoxpdT9BTgvK8H/nZoTraWj72YDnFm6yqtBClU7D2S2oQ1KRNTnosCpMxwq8uD30zudxCbiR4HPXoag2EzsiuADSL6kNNGo1P7gnJHRJm17/ij5WQBHtACQcEaQ4JjFoLIAjwCEPudkYt6wbi1v4vxkuoYh43Mlw5OfNRthXbLasQ4ogicoBrNtBBVVkqyrE0zGfGOaXCChNxN9oU+3gsJvajLq84ipmyZGfax1n6z9y+RkjwOFLrBdgXfdhQDV8XdorWsxCfz44/npxfXl0fX72dP0FigUZAGMsFg3LwYbr+4TZ7//pb+8ifeBLmafzqef7y43gIQthzz8fyvXYRha6+UD5dHx2cX77bL8Zu7AUDEboB+czfA+dnV1fxqC7PbcIzzq7N3Zxfn85PTLYT9piHuBSSDVB/n6c2aIqZtucye/q8IYuh05jwAdkzrBS0KWhzYukNKtDKn9iTGz5N1qWt/5llX48fnAJ6MRQa93zz86hO/YFBsyswZG/Sb+o/U/ffJNPSYFPdINSSHlor3i/hP6TYUkYuqrflOKd8JxA9P0j1hqJmUQr4Uki0ZKEw1HBDLPYG4HZ6hIFdRIvNVHBrUliln7zmC7UjgE0EsPptzBPqjP1eR76G1kLQrKz/y9bruO2NK4GaawmTIx3U51MxoBPqMx8CJ5b/pInTrFtxpYL04ohgc0OAohz1d70RjT7jPDaqRPcHx48Nqv5vXhqjOvRYGGRjUnXn7vOnErpjeGHH7/NuiWOJyYm3a7YES9Pv6vLsrRQa62omxIJpYX5RmXtyvtge1s6KBvJYtXduBMTn/4vb6Th0E05LC9SOHuf4Te8v8+GqGJOMHn4xbu/CgivBmq4P5swj9AdIfOjYM0mYu0QIya0Ul5D6CN1KkNu3caOLqY4i6vXp7PHkHd6UB/VYnugHYVIiR5w3yVjbk0YylHuM22uLhCGKawQham7vjDOKVZTVhPMuwC2u4TsolXOMUdSEhDbg6LKVHctmaVLk0fzJcJZqUFEVG/F48nO09hVyaRARCC2NIVRxmRdVWdsgbXnEMQTq4EVjSRjJAtxN40daNih0vVDUvQO7s9SSM2UTljM3sVcOXuLm0gvvgtuoq3TC6zmBzLUEUaNFhEv0DdnzWbg==', 'ground_truth/expected.json': 'eNqVklFPgzAQx99N/A4Nj2bOIFskJsQsgJPEUYIsexCzQFtnk8HNUqJm+t09hmFP2/Cp6f9/19/17rbnZ4QYDIpcloIvN5nWQpXGLTE86s5nfphEk+TBWch7mabDiOUesDT9Hl7cxXTh0nmYOCO8u/SxvVid+RRN3CCcOqZpoTi0x7ZVyHVrY3hnW5aN9ti+vunsWRDHNHaSeO6jQONgGoQz6vmOaQx29SrxXku1r7fCgp8bh5Bte2BQ37+0b+5SGNSlxgRzL3FRseYJUeSCc8Evc8gUJxXUigmCjDejjf0ZHCngcLP60UefFsmUyr4Il4UoKwn4537cg3PoR1bwQapNxmS56gM8Ntl+QAbruij/wzy1LqeIhVQK1BUouZIIFlojuGtvc7z8rR3UWiw1wHr5qrIVDkLvmtzICapRuw2Y8gthW+PU'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('wifi_board.PcbDoc', 'C:\\Users\\Administrator\\Desktop\\wifi_board.PcbDoc')]


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


def _run() -> bool:
    import uuid

    runtime_base = Path(__file__).resolve().parent / "_runtime"
    runtime_base.mkdir(parents=True, exist_ok=True)
    root = runtime_base / ("engiworld_eval_" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    try:
        _materialize_bundle(root)
        module = _load_module(root)
        func = getattr(module, CALL_FUNC)
        args = [_resolve_arg(arg) for arg in CALL_ARGS]
        result = func(*args)
        return _is_pass(result)
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("true" if _run() else "false")
