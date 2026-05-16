from __future__ import annotations

import base64
import importlib.util
import os
import shutil
import zlib
from pathlib import Path


DESKTOP = Path('/home/user/Desktop')
ORCAD_CAPTURE_PATH = r"D:\orcad\tools\bin\Capture.exe"

BUNDLE = {'_common/README.md': 'eNqtVMtqGzEU3Rv8Dxey6AM/2u1kUYLdQCElIQ6EUhdLnrn2qJZ1FT08NWTRj+gX9kt6pRm7bmi7ihaDfXWf55yrMxCLkrZbMmMBP7//AF9LhxXgTuoogyIDVsftUpl1v9fvvd+h20OQfvPCg0hOI7sXbNAbD4Eg1AguGsPucO0mF1OYSBuiQ9gpCaEhWCmNHmp0WKSEj3DJBvjjPMItPbU9/3lMxYdPD/zF9vynLS4acht0o1BqcZhck1kPtdoxBXel5r9kGVQZoJGhrBk5sWijFg8RI47FADxFV/KNNHsQr9tsX2kJlSNrOY8yA9jSDjNBoiLDUV0DTNVCmUXZcpSpfISbfaiZ9hq1RXcOjVMhxTKzKevd5GrAzajgYUUum1kTlSpDpjbVkFxWuv9D3++dncEsSBeihZdkSgSudlSLR+9Ze6+SoxCi32uHhGkx1lRKnTAYkytlNU5i9OODiH9D2u8VBZq1YouuiqK9KAqfanZJ+71PFFnxFHXFJRHE52MEtAFfIAdgdd4ykIT97yZOqREMfIZnwp1JU8G9MhU1I7hCucPjpGTRjDo8brvNYYoOO9atWIeDpQadZ2Z4umkxl0aWZCo5t5myEX5LCM2Pzc1zc/PcXP4O37yddxmB509csL+VoZ4HmlMMNoZFpdwRnzvu/xCwRoNOJi1I8FupddICLDUtB5An9qBCp40BpImtU4Z1Im4uZjMBYxCXFx+uBDQq1FBhkEr7w+j39Z7Ttvi1qudS/Eok8RvQMpoW+wNsSSw8pX6X4jtjnt/hQ1QuNzmRFSZhXW+C5Jxr5oN1XVIiO5E64N/Gx2121qpE45GVhrxtKb0y7MXx7Sw1h3n4OBter1bsOvRhz2pf8/RSp3QBRzCzqiWQNS3BYNPvWUe8mz4nPHlTmyy5JUI00cul3oPX1ORC7VWtQhbPSVtul3PkB1htudw0LXgql14K3k3G3/D6JfWcPCNsQ2cd8pezqAp9QMsTM3+0ym8Lc/ALEa7kpw==', '_common/run_in_capture.py': 'eJytV1tv2zYUfvev4DQ/yFijJcUGFFpdoGjcYUDRFF6KDUgChZaomK1MCiSVOPP833cORV1oyV4xTA+JdA75nfvFQRB8oJVI1+RKvXt7Sd7R0lSKkSdu1oQSKdiZXktDrtOCfJErQkVGnig3JJcK+I9MZTyFL16wKAiCSa7khiRJXiFKkhC+KaUycE1IQw2XQk8mjiZ186arValkynRLMWxTImb7zTfte1XxrJZTUrMu+KoR8gk+J5PLxfu3nz9cJ+/efrr+vFwkiz8XZG55oQou41upUprdGikLfbvi4tZZHLEtC2aTySRjOUnSmpgAMZyRszf2fjwh8DDxmKBgAJU6gi+upIgemAmDxcdff/vjavnhMrlagjP7KgA0XuZ5e79Gw0cxkCVqFRtufdxxRkxqFKU6MWlhr4QW1cJYlbVRcR8F2ZFiWhaPYFQEN0up+TZsjV5VvMgSiHKiU8VLE+Irz2JEekFQzEpmz+6TKZUcE4g8OA4e8vRrrni25ZA13xNaGXn2wART1LCMrJ6JqkTCRROIqHyeCLphuqQpI+yRFiSOmXjgT1IVGdntLOQjVZyuCkYyyFty7tNAnuJMk4uXNQMzjjwpblhi2NYAho0qvu/3DSI+mkF+Z+RGlkyQqT30dNdyy8pociZA4FPBQeoUjk4RpD2RFlJbuqXs9530nAuu1yDLF+iZ4alh7bpoSTQ3TJGX5+eEbbkZwKMLsWaP4juXtAzIzt3uuxsucomIGiyL48uV/B0qE0o3gYzpvu58UHtfpKr189mFz0PsacN8PSfnw/v49CIS7Fwi7QMSdIKh/2gC7QTEccNpwf/CjGHQkJjtE7IywQC2dvWAXCehR3Ye9H38M/i4l3Bx7Hw7OQHWA7LG36TUpBjtYSZjoe3qarNO2TXFtp/0UMBh4BAiS6NHnG/zgxnKC02mcG7o/YPAwhmpfgPSCJi1vISEz1rM4PZWBGTau3fKbUfCOHVoY07KiwqKQZsMAtgRu7jtrTP+JR6Pdjh5LFtFOJvqNuc3ltBC+73NkkCJXn+raS67Eh1D7hlob9BLak4piwJQQTUIaAymSGr5kePDnFxBF4jJCuYOMK5VxV5MbNdESt02QcdlJch9o809SNE8YzBnc+jb63Y4a1cI3jC+bzS+t4MYAXtTDHuxN9SacYSF1GNEdXqEs7ifvI36XohLBQaHeXDje/SuVRPg0srYToNSclkJGCa7nrS9G4v4uHnwnhaaTRrtGptG1DLq2denPVsJ6MRfww6abVNWwn7A1IZbzy0whQ+sobB9WEpdh+AwXDQi/PMTjMs1297Er+q+b5ejZkWJrhmuH1Q9X3LFUiPVc1gqlvPtPGizsPM95EcSzAi0MLMpM97TAr6bRaVmdQagSm7nwFM/wtTst4wIMqZrec2YPXYY+MEAOeoKNjy2CHQ7QDf+Z/AqUplx8TAPKpOfvcIl6j+nTmF3UQA7miYnr9fqQo41Zn3zTSwjFIuVtGsyad+3xY7UOfnYn8mDHHSHuoU2+oRrQ3gDfSXsWQRuQ0qj5uzOVzNjNLPbxNz2nAj/wB76Q9eB/Ga7hjz0Tr5uIXz9XFAGZWVbSUvVsKpDymuQA8OVvCHnQxR8XMliMxuT0uTISPEenBxNkmHchmFbLJdXS2J/DLiuEx9EfIjSqqXARXXGH6awzW+p9DxQrCxgUAezcVSvaY0YhlkQ4XAAF/N6a8EEsu7Gj/FAIOd/d97JRs1x67ZtDRzByM7qXRuHhMMy+ibzbT7qgrEy9MajD3XKgKOKI7TNV7ee7dq62Otf2h+l6EYwJKtSlh0YMKo47Bq0KA4q2gVxEL2DyCJ9aMCgP3SWwW2D80jAD55w3Lv2EDam0Jk3vzgfnnTDbWH/wWwbF3hUk1bQV462jJ75NhEWyU7Res/C6nKhCP1tyu49NkR/9xznfsV/0VL0l5MTK4CLYtuSPSMdE+EiWMcy3SpxovBdmR8ajOO6F96jeZnKqqjLt6QKfvQ1mYhKwFQa23es8v8AfCA1KQ==', '_common/worker.tcl': 'eNqtVttuGzcQfTfgf5is5MAu7JWToi9boECRFEgLJC5sA3mQFg61O2vR4pJbkmtFMAT0I/qF/ZLOcKlrLNsoohdJvJw5M3Nmhr3ed/wcHvRgZuwUbeoLBfDv3/8A4L1QrfDS6LgHypgG/ER4sK12ILWTJYLQYBrU8E40vrUIDp2jS4TJsB/MDLwB1GKsEKSHY6PVHDRi6XhjjFAajWB0gdCQkR2Yk4xRAN6kcOWF9fA+GxlbiHLkjVFuNJZ6FK+k+BXhWJlbYgaygkpa58HLGk/SDuRtChdM1U8QrsnRd6auhS7hs9Ql8TyO32e/7Ows7/+Ywp/CeYycwseZ1hL199lAmUIoDtUgEBx44aZucFMQlNGDdXw3LmcZ6ltJW6rMsu5Eljn2M4bvgsNC0dZS354G3jEXjVHKwRNmu3M3f7XYIicT7ZwB31JgC6NLlwL8qufwQ8h4JSk5lWnJY7JB0ZcuOlbCccyz9A7MTIMWNbpGFMhwlbF01qigkxMQHYCG2tzTVcovU04HnOIBuHZcSkuGr2lxCe8KKxtPIAxnCdmQuXGgY2FmpSfPg23yoJSFhz+uLj7BWBRThi+lmwIJUkAj/ARMtaTJaMXEGMfXj1nLaTOHqTYzB7PgIt0mQU9Dbvn09Tq45H2JSo7RCo+k1lpqWQuVAWhD0vV87JR/41ePVgtFP7A4hbvWceLgS+fcF+bTOrRnrm0aJclbVp3sBBizuhJ8Y01Bmo/hoZwqtAy2JH8CbmJaVUJFtcOVFArJW7K5CqPj9YlwIXCe8kDRQFWxi9+3XxwerGQQGsVjSoaHwwMW+b2wMlR/0OINSQCSl+k22QFgGYX7LwUIwttFWQYe4Hxnx8tielM7bjc/ndPmgh3lvDxRqPCw+MbRaKFbpU700I8rq6P8aVrKVzIarpCj/HIQyqIo50ucZH3HImlFd/8X+8K7J2rdcij1espR7O/c2NzavuTQr8L2plvazz6EBcufYSZ8MeEra0PRFe5eLwgvjZvnorvJ7Px5ZoRokdhwzSTPMmCazzLYVc//ygqL5NWGSmKiIRBc+nlnxg6GyhlS3fBWmTGcaUPjpVGCesqZnzfUNWEY0nhnaKm/UXGh0Sd5nsdcG5JYMWFM6AfgDWWyMa7viOWFVOFQvn2EEl03MCyoEKcMWFMjjv/ikMnhLK4nRx+yo4/Z0VWSv6QCRsN+QM+Xsc6gz4ySbQa2IIOssk32/GkbRSNPQe+cAibpGRDH9I4XC0BrN/53tVosduH2EwX47fLy4pKbeiBIPAky2b7eg8/Uj8NTKaXdrtA0DY/lhOQs8Lzzq84fh1tBc9Sm22jsOKFQpp23rPtaUJ0kIb+QsIFksaWCVdsMDPP8W7iqhGF4xPUD8Cx/xP0+HeLt7S1Kt0Pe2wjq+mcPPpIDKxfZJ34JpNtZLKkcnyK8Ph1z3QWQRjRSUFlhnNmAsthz1mLQ8/JsUP3mhfglKprn0F/OgU46e1tDHhtID36vyEd6NQRb9G3xLL5vTnmu3/P7iQriHrVEetGR/6y0odQVvyHIiHvcShR/Dq9fw6v+U0dWkt0vVWVEiWVKDw6lnhpo4VV+K3XaNcj/AKnJ1W8=', 'eval_inner.py': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('BCD.DSN', '/home/user/Desktop/BCD.DSN'), ('BCD.OPJ', '/home/user/Desktop/BCD.OPJ')]


RUN_IN_CAPTURE_PAYLOAD = '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'


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
    helper_path = root / "_common" / "run_in_capture.py"
    helper_path.parent.mkdir(parents=True, exist_ok=True)
    helper_path.write_bytes(_decode(RUN_IN_CAPTURE_PAYLOAD))


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
    os.environ["ENGIWORLD_ORCAD_CAPTURE_EXE"] = ORCAD_CAPTURE_PATH


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
