from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\Administrator\Desktop')
BUNDLE = {'_shared/__init__.py': 'eNoDAAAAAAE=', '_shared/common.py': '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', 'eval_inner.py': 'eNq1W2tz28bV/s5fsS/9wUBFwqQsuw3zKlPXkZJME9tjKa4ljQYDEUsSNW7FAhIpjvzb+5yzizspu63DsU1icfbc9uy57Xo4HJ7cemHh5UkmFvh79vfxh/HhRPzmxcrLfJElyUIktzITnphORCTW4iX+zeQ89+JlEXqZuCmC0A/ipTMYnBU3CuN5cCvFUiaRzLNgLuYrOf+khHUbeCLdzJMw9HxPHIi4iNKNPRsMhLA8W7wt8rTIReplSiqHBm9s8bekiAm5uEnWM+JA0/94Iay7IF8FsQCzUWR/Ly6FSsG0kB6IW88dDNsiT4CHPovQy8d5kopUep9ALk2zZC2OnL8cHQGfPRIqAXDuhVrilQyWq1wYsCnAXojIoGoTZkbntjhZe/M83IjvhB+oPIjnkCT0YuiHEaoiW3hzqYQvc+hO+uJmA16yMTQERYbSII+TLAITByJZLJTMxTwsVC4zVi8I+bY4v0uECpNUjnleCaGEFyXQU76S4IFISzUTR+aX8HLx5wmILw2dg2djMaVnYWG2TEWY3GGR80BmtvBivzVzyjPrOaUi1MoLMU8UaVrOdcQ5GMhk5AUxLRsjEYFivmgRoOWURZG2ODXPYu6lMyGNBhNM0NNWnioVYk1GAn8Opnapf8PExJlgjIbIKOQ6l3GuxAuHLGVKRiDmGJEZNA5i1ouReK7ByxU0eEjmS9GxixYgc72wxatQG8lYM6kZVGAWdpcmKmDrvxTzJEohSgyiRXqHvTSGAUAl2mKWNivqSGjtl7pmxZdqNYPSm69g22FA1iC9GCoK4sqwPVqWj9g1QcbT+flCP1urJAvuk5jMGnL9E4YXJDFMi1cjKXJiq2V4vH5YLRnDYKVeNb0hsBS0wArLI8AenEWRCRX4tFWHw+FgkSWRcN1FkWOi64oA0mfYQXGMXUVk1WBgxiIvX5W/E1X+Upsagj2DoNVPB4OfT96fiGNAOikmOn6QxV4krfLZu1H0bYF2EIKybQ+ASr8LYiWznGynhCYxGbwc+GcSxBaRGImh4wxtTDeyYBlgNQ7WERurlOdsnmTyNXlG8QQ6+5c3EydHk8PBYPBEjL/dRzwBvpN1ql1FZJwxXCMk581uRdj1pEnYhhuQgcde+CzyPkkXwNjKDlzrN+dpcPr27bn7Easxxb7TTxd4eomHk1cfTtxLPMD1Dga/vv3HyXv37Ne3707cH09+wvCfaYYefv/LGa3o1HlhBn55c3ZyjpHG62dsJg6iicU/Ms+Ho1RWBzGW6/z9qzdnTNmwcNDAA5Z/faVZfkEc08MF054MXtOokeiZOKSRi3LkwowMfn/3riMIi/7zhUsMWwZ4TMDiT6Ihjm0waATvf38DcJ41FoaL1nutkhr4T3vk7/AD+d+dvPo7i18q4kA0cJKdftYO7cWLweD927en7s8nv/z0M7Fvpo5LzWngaQn8B9j0j69ORCTVCvHG8xE0LAX3LMfLzEtXwoM/kiMSPAvWiIyQFzlJhB2QJ+IuyUKfYvxc/gGG7cuFcIknl7izfE+65B6QnZBzhIN7L+HYYgQfYmPMbAikRYg1b9bPR6IM43DNfkBx/nyNOMOOxCOhHfKRhMr4EZMFDXiMFXJcjjmv9XfNBAPB6bq3gLq6rh4X9aNJF47FRKNkefLEPVofWZGRQoeLYzhVx8syb2NFI+Hnm1QeY2QB4fOXR3YFGSyE58AHplIcw9CnL0cNNPTJtEY8B4GCwKyjkdg/n1/uRjDoDIAbuQE6uxblzgs/WXHiwzp+a2CJkzhM5ohuWvxqPIKUv8FzpxurxRCimJfnmcH0VBva0w5bebZpD5QYI/HXSqeEwdHz7RawXM9lmsN30xfCXh9V6ilVDVLODReOHGMp8yZv8xWy6kzGT0dYYlsA7Oq6jQvyBAoRDi5iLq35alQZEO8p5yedgG/eAKHdZ2NJFrdyTJq+6b0nzlJmzEmzIOK0RvXR0OdWGatS2q5Sh3aGXD9mXh1JbpWjgns2lcluIvSZI5cJ4kLuBFglkWZjBZXMP1lXt2pEj0jClGURATLGq8n1SExt+3o3K3fk1AnTX0XknNtXs5GYPb/ex3VpTykWTIuMWOzLnkm1pvnr3drSU+39Exc014F/iUhN0/0kajI0odye4ynlvjsnyVDJ/1Lr7JYc5M0y9q07ey/MooQhxsryZje48WUHx+KuWrP2Hgu/ZPt7bJ7dCEFHxreQkSsycnLBem7DxultTG+VQ7uyY/3aJ41qd2VwgjfkvFoxsx2+7V5mCQxyQqthj7ojjT2DtK7cMR+0ydxqy2bU+sVp78XChmURCquNwjDwYSROBybemdLR1YWGRa9GphCAnwuPp3KM0KaXgweeY6AOia/19Cr2KappLT2/nIaCQkdOJULUxVR7aGojxsK1zfapnvN0RqLEvt4WpIqnGglesP/AAGi5ga8wcuU4zvWDUzLD36ZiqqIiLWAe+ByeaR0lCguZebm0TpsxcSRuYECY9uEKgLA2uAj9c1r/PLyujTDWWp9j2ZR1g/zJo/n4qg06zow3CgNk5ksuPKy4FY0I5P8FlDztuLzehmN6yBcxoxrzMcZaoXX2k5xM0bNrAlwbSII6RXkqBz2/bnoELcpPxDtTiWaSiz+FggO8Lqoyl15QHRKGElU5v1bBMkZZ/ObHDipdH+slxMRlJqUjxD+k8BPx5u059ly2xPuUi2Y5NpW+ZquDSiXIXG5g4qaIFn6BgniOlUReWFBemAcoSudJgXobdWMAgsmdkdHphk0LNaPV0l16Vdog1ju2bawlKgQby1Nvh92ujUpuYPMxA0iMvV7TzHrf7PBEgC1N+br0jLDUvkOsl/E82+GCbzLpfWoZVZKXc9pUtV5LWtsepsYmHPVfVhvR3/GysSkhw3Ub4qHlfszqGgfEfSyXsmS3blW4vlwaL1L7mlecXN/I/E5KpIzGtkj7ZKWNPsex8FqgsIRBo7FGMw4uR2T/IAOLVE71LoCRKlVQvXFwOU6TgHbhssrc5/eUA3prBFIHrjoKYot/GENiHPAStt0SmIs3Q0pXct4czn5+T+FCa4FlcSkJcE31YPEQ3HGtgN/j4F+FLjnkuqoy8pXHXUrpZdSYIV1oky+ZvsW6gG2sncmEjUusHEDDDtuB75ZATnlB24ZEKB3PRySPc+u2LS29+2N6IWWX+o8p/STQuwk3oJWlv10/yIz6FcWGqvNjFEmVWaMtxX2keuZIDPWDgypuaDcTg3KGXCMgYqnrMlPTYt0OuZmlQYYj7cJhag2kMEClyBXCAraE5GFod7MNNR/sx0n+pMWmSJEqyjgfmkSmVQhRcgBxGzVyXZp2ax7ywLIvkq5nqbvflIhHhMyyJJuJrfy/bL8cUOCHKiPkUoHqotP20NfRHcZJeUKx+aLeWgi02hbDbc3Kg+4EjMT2tDFWpUWlPrXl9o41/jN71g0DxPqI8vsPDrkhD0t6PEG+hEf4J/NoloaaAoAdY1JLqBuQdtfudBINWw6bohlmkTrHpjuGaHZMjfbDFuBi+NH027FsPGHmHC0eRPQ9hk3ncqsRlEvaor1xX+4hPa1IX+wjfdEiPd1L+qJLmo6H3Ps+3SiG7646YfvI3rvQt9gycJ+kxi22GkeXMp087aS81pR1M+4Ryt4alNc7KWvcYqtx8PsOderiu/pYq89CxQMLRtlPo0+4j6PmQdlWYxjr+RV/w/aMem0a6DWw9dkcstnd3TK3v3im9oXdUlUF/2XB09JjHCBWszI1krYyQxnr2K1sckbfdVS2bbx/aAsFBq1KP9+B2fJo6AC/OnosD4gOxLQ6U2vo7Sz2UrVCpNGSPeMsi2O6hJ/amNyJnhdFhpQhMye0Ok9m6E4NtbNe0IBlQvlILtdIru3O4i5sPkzacZxGKyv0wZl4bHGDRY8xqoKLlDLBMDRpfoMFNvAfqOx62ZWtUb3du1yuQgtYtZ04ZgfOc+yyLo7rXvghdoxUrhZo2MuhNcu94WFzwUyWSidxB43jxeGg3ycyGpDNuq+2HkQ9jdKClXKai4rsLibOEIGN6A/dfejbIt9z9Dyjs2V9OmytjxCHpq1Hg6YuRArFh7xsupa2zs+Cz5htY4Ns+VB+qtU70k2a+yA1u2dkrK9TL5HocGfwCKJ7TkRODOm6Xp5yA/3nFFo0umcxLRos3dcQIIyqmtpO2JIic1kZe70Nv2Vnc9RxNgvKMcS2BnooHQ11tFjDZgG7/sWsCcCutt2DPKzqAxKd7jBc0cM1r2DP61cOZXu1eLpVM+dw8fC07rzp19fdeKVF1+u0X3j9/oviG7CWAowJfIUKukeARgXd4W+mgid8x6OKDpqT6prH8Q9m8aiULaVYZkmR6uYM5lEtkhtUBMVdNgZh73EkIhndAJfebNjVZWBUbvKJGuCDPRbG2HqKH3SbIX2b6e2UH8RzOkalWe11J25K0U1MKZlrr3+H7da7odaQpa+82C1VWVMzWGmUblVk4QZFMjW2EH9bq4fd2SE16HTOxbCzRFTl3SQoD01B9awUqOtTzR2Y8SN3YIzX/9y8AdMIf/c60lVHelcTaknwP+ROtG6B3q1boxX7aTd2tfpI7c5lI/hhOYkqtbjo8g1Pum6tIbh3yf0hhUr7m7bmhs1nuitHasBUm5bv+NTXgSYjqKKRAk+Hdf99F5k6PyBtHzeU0jxeoFEu5lx9gLKrOQMYas1Uc87fceuYoqbVmm838FLJlnPNdv6uXbTRc6dq4xmSgHMu3fIo7jcIjIKxW6IdCQW2ITCYKo6vQFR5/GBPD5PgpxX8ntLLONfSassLV1tNTCfza/3YqMqGfRSNQo3Z42macrMDMF+7kfTIcC1ogeQ5IKXgR3nBooLctCCnJeS0B9lTYXlFbLceSxbG4nWtxEprJVm8/TqVaWLC2hq8rCTEE4OIH+3HVWZtX3+kKa8vHuyGrnpy3e8xjLLY7ZSctSV8TU3aEetSB8u8ro3BYF7Xq9ePi8TpEv5cHu8oYtvnk0/EKTX7uYVLtQe1AcwdU48KhyDku2t0o5NOMKhvN6cyIlCcNYcybxwJ7N5OzTZRoTuvZaGl3dFjWq+t6X9Cc/9181sBBWHttLqYN2tfLtRXCA/XfEGwPEehFT9cdzJ0ulFoAL7XJ0DcNSZltq4mOtX9DHJeCJGeUsFiYxJcLiOalzU2riFaZ8V17GHowb6DbzLKZv015RquOwqf0DijW387cpOd5KZNcuX5bkl1VMvbCkuNbKpRSq9RDWyoYm3pUcP2LEQXBDpBpnXub3ImtGYqh3XOttEDOzZx305mJnNeI/6SOYzM80Y/X+zay3X/QhM9tHdu3/1iVOberk6QOZlt2wnxrSy0JlBAm8UObRroPiOmyviSRouuRotHNNq+w9vUadHRafEtdbpDlFqrnZKnr1fjRvjmXUCd/LH0l3QIHAf5ZsYe4IbKKi/bVAdsvWKk6Uz0lWFFx7Hk2xuXFK0jh7p9+kA4TFB38KETUic+2PLyJppL5L/lRLoRyJ6r/E8IIV1RLpYrpM188BmYW/B0+Tc3JQ4J5Ka54kSNkmVs5Q90uYejnEFtMtrD61YaWU6FB2hZWb7mlG7NOV0FRTgn15zg2aP+MPK8Roa3YQybPobpbgzTLgZtHC5nquYi6xiG0rqH2gPe1Hdc9wPnmSkFuT3MUo5ZZGoOV2TLxOD5YO/BuMXyjVnY5txNNbe/IWv7c8n++ruRudux6+qJbBwmnzDL+zDbtcG2LeGq/LXFNo9+IYmtdFKhqCTdn8nsFdjs2T7BhK7/b9uG+dDcNuLycyVwua3rUy192kn/OcMykbm8p58t+YQLcWhV5EEIy5NRSgeGGoXH/VQD5LzKlkWELOcdPWXGIL2UhHE9884ajsd+kEEWkPSKMD9+g7rQgGZL2oqYwfhojrJq306PdM9/1rrsUo7u0GMecUVnOHaiTz79bmyUZd49qjVX/qkrEvtunhX5qpGM8c0vvvoS0zRKFkDZWuadqxwqm3cRL/MRT7W7t05KqEARkxam7rgX4qvcZcLYevTtZBIhZC6tobnWP6yPbId0kfHxS4ALZsVRuYeSlAroGo+texd9VnWDlIxA36AFo6O2iFD3qOLUtvt382pRSWu7JW2QyDMp95HpkPC5Jk4H9bl86+jeXKBJM7qbgN2VUXkAAzWXFLwAEp9tELKik3WQWxPuvWIThqFL13LpDI+UMqW7GXjlsoSuS1F+6Lq0b1x3qGXRm2jwbzP4d1U='}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = []


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
