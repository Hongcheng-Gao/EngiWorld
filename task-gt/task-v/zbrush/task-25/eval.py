from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\Administrator\Desktop')
BUNDLE = {'eval_inner.py': 'eNq9WuFu2zgS/u+nIFQcIiWyajvdvZ63Lq4tskAPvd1im73D1WcIskTb2siSKkqJHTf77DczJCVKlpMuFrgUtWVy+M1wZjgzJGVZ1tVtkFRBmRVsBf/LQNz4n1+M/PttFvGEF36cCl76fFcWVcS9weDz26ISG7YJBEsztuFBlHAh2Md9uclS9ubje5eJjJUbzpY8DTfboLhhleCC/fz2H8yWo88EE2WQRkERDbZcbIZ8F26CdM1Rhm1Quozv8qwoecRu44BdZ1nCXrMranMYcEZ4US23sRAxcJWjQLhraMcpSI6f/ynnwIAkYJMd/GNhteTTAWPngJqzVRBy9jFL9msgeY8zZcs9G3nfM5sH4YaJOOIOG75mcZoCzsh7uYP/NMwjkPfU3oK5kqpCoOHIm+BoUaU3PGV5Ft4AB2x8+yuLOM8lyNusLLPtSZSLkTdGlGUgOCim5GkEisFGRMnu0jvQI0z+VxGsYW4AyVguzcHBuF4Oggyz5W/sVR6Um+dl9jyryrwqPWh7PbAsa7AqgL3vr6qyKrjvs3iLmmZBmmZlUIKGxWCg24p1HhSC69+/iSzVz2CDjX7OhEQNsyThIWFo2HdZlZa8kP1RUAZhEgi0l+qvm1y2inkSDQaDTx+v3rEZO9DcLLB8CS7hp8GWW1NW/1lvs53lSpovVRD5BQrvb+O0oRp5f/tOkUhz+CVMCb6CggeSDMz/wpXUz9DkYCH4bI1BYr/Mkhp35I06sHsFbJC8VKgAC73gfkP0he4oA1UCT9rAIUft+dtgp+iItwb+KrvZ7v4re0VdcvAe1dAVCf6GY2/stkja/Dsy3AVJ4pebOLxJYdUbeKMapktS40mYBzDn32sTD+iTvdvw8OYXLqqknBIKmnYKQaKQ3oz+EU3ZEqxODVuxlr09WJ/CrODvYElIpBChxZQlsSjBhcij7IivAuDlw5KDyLefYacjVw50sSCKbMGTlUtyuIq/i2xddn7u39w5Ehz/kNCTXLwgz2F12sZ07CMERzH6e15kOS/KfcMWFCcJibvBo+CwMlOav23wg1iYRjjMDj05kIJ4COHKFOskwxKWd+ILVNgJjmNvxOKVBGvEYzyBUAT2HBhQfhSH5QmYw8D0J4s4olcQriGF26aT3ICww79DJmcJZIfQk45zaIZqzbjMAuVTA3w/DFj/X5/+Hhp+D82MC4zDRXfCSQxeD342t4YWBI6/vlwMHoOetuSgZDlj1sc3nz5ZqPfarKRw68c37z9YrRHETrvdymJsfkCQhwWrlfHqcvKAP3DWljPoHamFPdGNwGp1ssMZSnd20ivOUMizBzBLv4pXlk2mxnDeNf/UG68enG8XUnmX9d/U8n7L4tQmenD3ARrIp0TlQ5azMfFRwKBkjo4qFa8yiQoPc+xYoPGk0dZJtgTRbmHNaIqyyhNukIRVAX4AasGh7Cv7KUtxZvhl9vvrIqtyNK2KPFI5t9sgl0PncQpVD3wg9sHwMp+nApKybbhYmqVJFgaJBncJx23zqqnRi2QHiwUJ1vY53QlsLZVQrU/VEmsuf2zBqqHpQ+t8AT+wRlE/Tq0gyFNQwqAMglZuaTvt1aaVru2qJHBaRDglqYoeYXvUSWR3cblhEONSMjiIW8AEoArNojhdz6yqXA1fYktRZIWYWfE6xThEFeVqM20t1CK4w6VqNmuHBL7Q64E3xbndlhqUDSWTpAIQ/Aa6ABSIotnWM8uZHuktzNIyTive6iizGwwjEiFP4rLDqQzW0I1U89GiKwN1gnYy65gb2hg1x9SSIYjxdOHgwITLBgfK7bFcz6vaGw7Yq43nXIwfjld4jzPJ/PeHveibPOmbvem0Rz29SPUfTwzN3vZodueyvcvuschIsqBUml04rvl70vl9uTiW1Iw7elq2QneOyesQ0TvlOVrNRHQwxGCjmvZc2aZHkC7FE8K0NLTu0dCRor/VCfstchzecPEdh7ij6Rh+BXOKaqeRgj0yqVXPpE6rH91c6rxJGN1ao7zBMKPn3y93HO18iDa43m9UMLCeW0534dfuA/RAC8nEViOdftiVJIVtwvTkMlRgR07ELsA2F9T9KDhMjrLcSQaNkrR3kdfi4B6PVO7RDAInmbHLJ+wt403jvi1zu4YIjvPnHUeXvHqbSrFLPT7o0iQWsIFL41UGmxGSjgoTrO/lVHi0pjJS7ZWVc6HD+LAFuRWUm3CcURYoM90Kp5XJYqQt8HTFTjvZJ3DZEkbdinm8QNS5HaNdHfYXlrZ9i+SZ27BBtHEQxDDYf8pHiCcXMzYedPcpNMTYoeACmjRFMHV7ePjEhe3UNRvZIsXznMSHobTTtsk2KKCS37Ksn/gdT5Izwba83GRy3yOHwQwEZHaoR3Eso1OGgOXyXMXD4w7DkQAS/P/yaMNiw+bGZfrDoU+5McXVkO7xAyO9bu4oWkEb6s5HqGicx5zU3ag3H5s9jQUUhkEJvEHTdj6CrMKGMBCzC5TE2DIBK2DLxFg0IKainyj6SU0/UvQjk/5e048U/aimHyv6saIn3eL8vwMCPPjxxJcCdrs7+IlyIvNzkgBh4elejvsAgyawqTwnBG2KD2CEMR+OJ99uCN0PzJ6zDy6ykt/3+A2EhG96lTwZOXImgRYVaFHRtegtmfTWWGR5Y6u4MYwgw+Sgrh8QiZ7H+HwvnyeStLtC9RQETiF1caj8ximk9ZIoqtTHgzwbdjJ+eyfTPeuAJ+BRt9pq56/K0kx4ONzjO9jKiBrO8FIEoLhmYaekg4L5xwCSMMRJK83oGDco2UGPNveUakKIMngE7rqoCA2hZm0kddxT4HZyZu7gamH1vg2joyScN5F2MejwFVD4J9xXBMBb1bCw7CEcjTvl58o61P0PTNW9NtDafJfzEM+jx3p7qnSKtNNeBWhB0bGASGdrQzbzGNNForksmhcoGx55zts0iyNxVTF/dsDBZ/jrbPFwZoh7diCcMxMHSRyta12eEHdV5g10Xq47VAKVQ1Jf9+lUrPw59fHUVQ7a2uO+dGXGXZjkCznwC9Y2th7+XHOgalBzq4+c2kpsznlBhYDzWmuucwB8rLuGAJ3wSzH1LlcPDFMcU0prQ4Daaq01/HUWB+49Sb3D1IJEqFK72EB8ivB4fyI1Q+c9PRBtBFkNp1k61GQKLy+4gPimBXymLxXoUJfJc1pPO6480aiRJc2MYXa/xUhPsY9CHxVFJmGA0RJz/0lCFPEYWw89tuCSBPX1xYbV0VmwFLYEGSrLto6yIUG9mrU7YJ0fW1vLcaAHZWuJoc1t4oKx3e4J1soC6A5xlphu8Yz9GEO5g7dT8rB+CDu9TN4PTVmCyKJkF/8ZqkqFbnzKTSCPZn6+xsC6n5GqPAX4HlanOtIXm6wCey85S3lQQGZ05Z3CSBVZmJF/x8sLT2k4jeIoKLmx+3i8gHR1Vn+qCjMPl1L0g9d4rzLtK52fwXRVYdY+yanZHKXl7mlGiBxeKQ8a0p3GtEbHGIz6zipUURFv2d0mDjeoUFQmjjnehtaaqXcEOEGXhcS/Fd8b2r4sqa5kVlClR02exDTZMfKSJ9kdwzsfENHImEdQdA3VQlK3hgjz2EB1LbT/M4N390+Nbi9uQ5Eig+qv4GBFwWeY4BtuSrfEAqLkLfpjM9LcxZ5ULFUMg56zZCVhDSdX0EEyA7+hhS79enbAT2p42gDHvDAO0fLQYajn+rBnw9pEp+7V4eKxCamF2Ijcd5y+sjoR7Fikvjh2FMs6kqmI9g2e1q+lWvldVe2boP20nvZPK0nFRSzdOxb/I9raPxLyT6lq36On3b2frVb4CsHM2BApuWBDdX4Oqf5CCY07Mmz4tjV5LFTDrKs343q4X3lf29rDi2LQXw049V6c1B8G4LYiGm7tPPhvrHTqS+Aphei7OMLj+RX9oNdKKF5nKTVAbPTYtXzAdgUUq5c9gBhGtqOqkAf+eyUFFpQySWA6FFsUAX1apkOAJA//v2XDP5XuXpvpbjJtsillkyKr1ptkfzrD1ZPVCQ5/OEqlV/hmC2qebjCMskLD4qslYCzOdrRVT7J0zX7HVxVclhUD/V5ETTP2XjY045ceexOGPMfXR/bgAdBOpqiLz1q2RkMwBR8FkpVlTdCoBmstRQA1ag/BM3aN14g0LWU2WRHgOz+kMxhYifoNHrUG8K4IJYSdCKn6+xfweOldfu8NmosYvJ6UzHFb08O8Wbrgu74mOBUeG8AhsaICtnl/5Cj24LQAd2hM7VBjtAtZhHMZhivEc37oX8agidlBaVTlR1A7NEkrmBmym+7752mWDFpSuT5l/lZRobU5lkcbfBtDiMTzi+bQgg42mkP8vMCDbGKtbtxVgSY7rKt/vfng/3L16dcP11ML4iu+kORF1TYXcpB+McGpzxjxLMWXr0CJ9pkKvXdGG+cZCuCCm4gyzNJVvKaGzu2xmtDxAY3TcFU85UEGWEnom1w8SdIvU3lvinW1hcDwEX8VdsRFCEsT35qa6Rf0OPs8fDFq3mmjAHqh38tT9srRPMiG0GyL3vsCAxX8SxXDftOozJTwuWeKpqTdBrDKlJzYoY9aNJW89kDbNXPHLnyjjNSMW1k6a/B9ujfxfYT0fXV9IvEH/wMLpoGf'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['C:\\Users\\Administrator\\Desktop\\output.obj']
INIT_MAP = [('scene.obj', 'C:\\Users\\Administrator\\Desktop\\scene.obj')]


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


def _materialize_desktop_view(root: Path) -> Path:
    stage = root / "_desktop_view"
    stage.mkdir(parents=True, exist_ok=True)
    if DESKTOP.exists():
        for item in DESKTOP.iterdir():
            if item.name in {"eval.py", "_runtime"}:
                continue
            dst = stage / item.name
            if item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)
            elif item.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dst)
    for rel, desktop_path in INIT_MAP:
        src = Path(desktop_path)
        if src.exists():
            dst = stage / "initial_files" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    return stage


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


def _resolve_arg(spec: str, desktop_view: Path):
    if spec == "__DESKTOP_DIR__":
        return str(desktop_view)
    desktop_prefix = str(DESKTOP)
    if spec.startswith(desktop_prefix):
        rel = spec[len(desktop_prefix):].lstrip("\\/")
        return str(desktop_view / Path(rel)) if rel else str(desktop_view)
    return spec


def _run() -> bool:
    import uuid

    runtime_base = Path(__file__).resolve().parent / "_runtime"
    runtime_base.mkdir(parents=True, exist_ok=True)
    root = runtime_base / ("engiworld_eval_" + uuid.uuid4().hex)
    root.mkdir(parents=True, exist_ok=False)
    try:
        _materialize_bundle(root)
        desktop_view = _materialize_desktop_view(root)
        module = _load_module(root)
        func = getattr(module, CALL_FUNC)
        args = [_resolve_arg(arg, desktop_view) for arg in CALL_ARGS]
        result = func(*args)
        return _is_pass(result)
    except Exception:
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("true" if _run() else "false")
