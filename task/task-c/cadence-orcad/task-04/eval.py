from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
BUNDLE = {'eval_inner.py': 'eNq1V1Fv2zYQftevYIkBlRJZdbsNGLx5QTekKIqtLdZiL45HKBKlqJEolaQSZ57/++4oUqLtNG2BLQhskzzeffzueHeklPKbtE66O1K0kuhUXc/m3y2I5B/7SnIiUl3dcPL8V9L2uus16epekaxtulTy5INqRUIpDQrZNoSxote95IyRqulaqUkqRKtBQytUENg53ON+N6m+cr8lH7R0MFdXl07FWxQJXp7/cU6WZhCCmaoGI1EiuWrrGx5GCaIROnjx25vn75kRlXQ1O12fhWeLi/wUP5OL/CQ6+we/TyOYWJ3ztRHB8RkNgiDnBWF1m+YhYlgYa9EiIPBXFQROYrAlfFMprUK7gn+Sw7EFed0Kbua0vDtaNFShcmW0A/Y0Z5pvdMhF1uaVKJe018XsBxpFZi/fZLzT5Nx8AYMkVYQfqd1SxriUrWSMLkhB0QzAlIqTIq1q8MaCbPmO7tz5JK9Zex2WrQZxwKNjcpuKaYDruq3HcXqpvDEQO0/mEZn9TC5bmA08KCCJasnMKIzIT0vw7ybE6WHixCkftUYWlQHMhlgLkZQFUVoaM3mV6RUMYtJefuCZXlub7a0CMKu1GWHoFhCyqLiJibomlQBjSVGJPK3rcGKtoH9dqJNw6yJlF12o0weHJ9/QeNyP2GLPB8nvw8gPBkCWpF3HRR6GhrQQoUXxwCDw0Yy/1XVkvQ0BVnMR4mZgjjybewrTCrz5Z1r3/Bw9HRaUbzqggud4L9Ut552xClrbXuRkO2raUWAYdeRVURi+gJoZkmQoY/t8wY6BTnAbAw+RyYGbyGzYoJzRFfme345Yqd3KUIjlv0BM2pmJNSqb/XW4DeqjBDb6JtxAlGwObZEnhpxhEHmaBOvaSmgFasYze8tdqhRXTAFZExBgd55870mhd5jSqdTs5d8gh1pW8zX8Hwu1nSczezoJufuFyZQNqVKFwzecdQrlwa3TgktqnuiU1oxsKhTDjAGS3rYnhPpJmBrR4QKh+SNh8DO7UXD7IdfDyiBfaqfZ5FcQKyVGENOy11f0fiOSm7y8hNSD/AIZL9Ja8ZjQySI199c/1C7w86g70725FNWvKCBFk2sw5MW7LUJYAEhTKQVpE/KbU7ejh+lx0Oabnjj6auO2Fr5911UZd1AmFJPmT+JwDgW9Q6FxyMckgIuVMqWEwCUIK1AOsSkyjrKxiaEIpHKUTEquQ68ARA8fhcKWWy4H9nqBFSi9rPkXkHYvii+y1fRKk0tOXr1789pm8AfJKfXIjY3OkZpSf4qZUvvElPprefGj/guIOa7xOZfg+hx07VUyL9Y+Xe5jYmCqJUDq6jTjDzYAm+wz0doLhE50a7uA+4IWW4JN9uBtcbrtERquZZUpY8MedqChky2Yaw5q8TW/w+wdHpWDeD/7e37Z49NEQouhYGumUCvQuY72JLBdtMluELPI7hHFBmQUK/WBxCHT+0DcEV1RL6i9808qAdm+ysnjLejbPab7NrNW6Er0fJy0l8lrweLxDDH2Vd+az6fR5+xbeyRvuTIqoYZmV87VmN+J6cS28LGL0elk6wztIg/mAaIJDPL1VZB82yM88DKXypyRDHeMDHcs3Ic02CNb/DT4jgNprPTxfln3gA3Z09x92BaRR2OoGnf/Z6T6Rh5Jx69vCmYPWPZXEZgNwf+D1QMgjltr0UJzOdWZfDg//kho8gHoD524TVBQ9o83mqYAt72XXuy71eyKZ9fD+mrv8O6sB40KpvwOGiJ43ZnkbpKaSc7x/na/USFpKTl48bYCVvSV/4odumVTJjzqPGXr4J6EHwBVDLJ6g2/bJTDCWJNWAt9cA5P2uStLg8+fU3fKlv0Ozuwkkuey7Bs41FscSdfqdUma5yy1a6HfUVkJWWKqBcGh0ODYbsZWcq/7xLXEa8FsvoZbFJrHaN43nQrhYQWPJLC2fAaVSCh8v6cqq6qlaetsLYJTYLukwzlGjRwKrPF0ZMKAPI2CfwGsXxGW', 'ground_truth/abm_vs_real.out': 'eNqtl01vHDcMhu8B/B8GOeUDnpAiRVIGetist23aOHZju0VRFEFapECABCkSIL+/1MxI4nZ7rG4zu4/El+Qrac4eTE98TNPN7d/v/3w3oc48w/To1aevU4KUHk/b72OgXjBcYJom4GdJnyU5e3BWp5luPn/66/2HdxfTw9v994er3d2LPZ7v9re/HA43D6ffprd/fHzz9cubz+/efpi/vP84/V7Bsy2C3X7avdq9/PX2xe30H+PucHVzeL27u399mL7x56QzAEyXh++mfZ3kyf86lrCW8e3rw08jip8vnz+6vr97s3t+9Tg+3/74eAHOw1iAf78Ij+sKWGX4ODyFtBBpTqYZ0uEcSn3OM7AoqT9zQzAlQGvIeX2hYuB/sfpCZtJcgCOSspWUO0KzCBHlhpivUrDkiDCmTGMVm1HUmBrikWPOWlelhmRjKxQCywUt11l1C8NAl+eOqFrS0pE0W9HEOhBB9lkiUkpOkjriGRICtYakGYhtmWJDPKdkmjBoEVQFHUgWMjtCMqKZBC3MkKHKl/qC5pSKCUbE0MgoaCFfREpD3FliWGQg5DlNSS3UxSyr9lWyl5ZYj5DMhsQd8WrXnEpDZOaMtjRQR4ohaApavH2Ya+x5rb6vohJKyTOLGEX54mKWNsxb9VMyrD2WVsTL4BkLq6RZvIEW+blVX0WOEHF1ODLGMxajzAORBEV0IFVtyUpBvgJ68zbEq8/g/T8Q3ym0cI5+AVHvstrsrfq21qkjhSlZzJi6SbU0xKtPWAAHYnNxv0DsZAVaM8St+mIpBBa8T5v8VFxNbohXH8WhiHTv0ybfpwTsWrz6JIQUke59avI9x7g0++Z9V2sSke79higWXrYHat5XyVU+nnifmnxv7CXJG+KPJR0h3ftNPiXflQIiIMwWke79Lj8XNmqIVx9lDRRPvD/k+w6z1GGrfvLAKSLd+11+SpJTQ6pt3QxHq3TvB/ml5IEUwRp5R4L3u3yUdd9Ka8MUxrX58cT7o/rE0gOTGT1fkCPSvd/lqyjWauPa6gLuyyA/eL8h4v5Zq11flJlICWEgwftNvmTBrA3xvvXTxrU8BTjxfpOPpGXx/oZQ9l29DCR4v8n30srSMBuSXQyngQTvr0iZlYA5BOY7dE4cke79Jr+KL3UO2NrSPD9hleD9Jh89DKCB+InkfTqQ4H3edn7fxkCxIXlmt6lBbP7ufW4Zi6uce+Tgp2eOSPc+b2flkRYP1E8OzRID697nLcllSVlD2A/1bMuccOJ9bsfrUpiG+B7tVxgsEene59aWXOvvL3CdophfFo6Q7v2GVFMuL3C7BrldloY59X5DGGsvD4TISpGIdO83RLA6ZiDZh2pEuvcb4qeJG3Mg6osSDiR4n7eGAfB/hFWKgaFGpHu/IX5B12QN8Z4rAMucp95vCPu+PQLzC4q3i8BAgvcbIt6XpgMRoKwhY8H7DTFw/TIQl0LFItK935u/6u+BVTOklPNAgvcbksD1ByRhpiU/eOL9hjBU/QNhvwUWiEj3fkMEqv6BCBblID94vyEu3/UPxBK6gQYSvJ83I8OivyFcL1eZN2T5GPnh+vm0v361f3l/ebgcnyf+YXR9t3u5/Hz34upw9M0EvvLZg38Axrl+qA==', 'ground_truth/compare.json': 'eNqr5uVSUFDKTayIT0wqjk/JTEuLT3FSslIw1jM1NbA0sNQByxflIssZ6hkZGBqZmELk8uIL8jPzSoqBEmaGEKGCxOLi1OL44oLUZKBoWmJOcSovVy0vFwBHCB1F'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('abm_vs_real.cir', '/home/user/Desktop/abm_vs_real.cir')]


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
