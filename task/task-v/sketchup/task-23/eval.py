from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\Administrator\Desktop')
BUNDLE = {'_shared/__init__.py': 'eNoDAAAAAAE=', '_shared/common.py': 'eNqlWFtv28gVfjfg/zBgHjjM0qxke52FUBVxHO8igJMWsbvbVisQY3IoMeYNHEqWYvi/95wzQ3IkSulDbUgiZ+bcv3MhHce5X4paxkyuRbYSTVoWbCmzStaKJWXN7p9kEy3/WbGbu0+sEepJBY7jnJ4kdZmzMExWzaqWYcjSvCrrhomiKBviok5PzFqpfJaLZumzb6osfBaptaGPRSOiTCglVcugW/JZksosNic3eRbIppayPXebyVwWzQMuCcVuH05P8P99R396Qj/sZimjp8npCYO/QuRywlRT69sKJccT9liWmV7J1cLsH2Z2H5W1vBF1bBhGyFxNWJaqhk21xjyWiVhlTZiIqCnr7RQ3PeSHFLDJRBxzJbPEJ4V8o4eP0n329m3oGe74h+cCLSYQVSWLmJNFfEDqdTLeV3UJAWy2lsgsC/VZkmxLqCWEsCAncEuaB7GMkY5HgaYkPEQsLWylfiS0AShkoUKfHZM6DkYsTTTDXkcmMyXZKBjZXqvBdlkPGGVpAeiZsplz5rC37N0v837vkMIWaUfeejZxGJu9uP+4vr93Ua3OctLH/fX60537OmfM2eWx85c4L1FAQPvrxfkrgxuIzavj7Wncimy1PraPKn2VCvA0YZZmBx1mFDyuX+Jwiga464U4WBGaBOPk1bP1NCFy/iyc4FuZFpwU83RuYEQqUSsZlo/feAXp3QZlDSDA7BWRjsvch4/eek6bJQOUFJoAEzeZ7IYLZWDEkr04YXrhXgDZmVbcC1SVpQ33dk+BZ6D+wGHg1MxGczgtQBuUy903rjcZOiYqiyYtVnLACOnZdMrctXuAjKxsg8STrBQNb2bjuQeWm5tz++Zi7nl7ysrMlpIckpLGG3RhWjR8Yyx2/+J6QOOxMzYmj23QXSB6Mp8fYJCwDNwNfDz2tym7mBxGBvJ5Qj61KBaSj/2eCsR4k+N4pzB3fgAK0M1HvWdP7S/7iYFfjPEGVDZI9gEVCxlWpUqpi+xACzrPV00P0GftGe1jgBI2iiStoRTzTNQLCWVX74WirsVWNy4CE3aNKTSNgCRqGUa/skSo4YlgAR0HbluQYboRI4K1JKcRVvFQkDZQnDx0uAwasWij9QrROhubEPe6uCZWBrA962GJbJPnDavS6IkZywC3q6LRO4+Suk8uNrxn5LMnCb1H5I+xYGLCEEMCTeIukbo+G3mYJ6M2NMUqJ8s0ZCH0Hbo4SggauaHEct0u++Y7QZ1xZDFLIfD6giJv3UBGENO0h9pIQw2PINbOfXaBXFtEgMga2mj4XNZZHCJqUkAMJ4jsAuMPkT2xj9e3TEUSSsiiFhVMHADMbAvRFIUCwTl4xejKv/gXHiO2Z6oCGGpIanY/ae+yMmExNO+0iBq2kGUOeNgCphUwSST0o0jGPajMYBKVWSZiQVZXWyxxRWWGC6mW4F9zILjRv70tdrMLmzK83Fzy3M49AdRFFVB8ee6zuNlWcgorFLGrS6u+AK5EoJaikog8Pr7y95PY+EEEtaRz/NJnP+BAu0dYDCALKsktcOxMIt/qIFJL0Kvo0hDdOYV+RmnWO+AZwsmLMoYZ57MtN4fDn4OorLZ8V9mlUKJpakPjwsBZp5tBxYcAHihmyDRn7zuvI49Ac9iv2ZtIVjB90g/UngPMKpoXd0aQJeIdUs9WMFqmWQwYcrE9UiLO5pNBE0pVWkAPA6TxCODcYocwHvxmIPkFOB6q0QtE2zJokXvggAlAgBPpIkhjVGNB0wslOvhvSIQWVWRQUNVpDiV4LdWRDrFWBrJKg7YKEAly4x0+rtvdgfNhCrPfxgOggwuhXByhX5a5pl+Cz2BGnq0h4eG2hLmF87XSeKYONfa8+REuz8CDI6v3LA8evNnEZ5OL+REDe2AHUKuwCT7PwIw5jFY49/ODTf+HUT0WTcoIPJ53iYKhUBgKLC2aXO3NUwWNvwGCbj9IOsX8Plu9nUI2qF9t5exKkGU8NT47y2kghZPfZV2C70dY1z1PF/sWdtYoGa0eyzTmGzi3hc93+MQb+Gzh833Y/rXoX3zI51SNz3VXEQW7vv7wYVCRB4as7To6650y68Xj0LoZQSNALdqlnZPdHl5se5q9pYPccf/7ARFm/X/IsagPrWvq+X57uDg34W2OWQ/cYPA7R85wiZ0YL6HwX/nsZ3P5Du52FISTl2YbLn/2qeHPxnR5ZS6viKtFdE5r73D7nHiSpAu6vDSXwHV0yBiYYzpT2mEScNBD6XEFhRWHSMIZFADKi5AywGflqtmfHD4gATRXBXjJJLv5+93d9cdrnCUCqpCQYUo/4cM8wBdp3D63a7wXMblSY7G98wLN3pK9wwVXQs3FZIPfTykhHgvLOvwChavl9H/PGcZnMkmsTWhysk5FFtwmiYwa7sD2mXmB4fj08ObgDAmWwm2cJslKySkfBRCp9qutG8DrEOfP5oI7sGTxdj52lyDU63UPJOnSPVXs7baMu31Y6CoiOTMXFT7hvvZF0g4aOFq3Y4is/aKljiztVbmqIxn8iplzT9d8t3jCYz4wfT0jDJxRzMGQdd+hfMbdf0Fzd/+NX/9x7UawsCS13bnr5hyt9G2VZ6Cb3azSohqq+qmoVs0dtZydk9jbaQ9rsPv77deHW1Qrcd4MDbAosbWDkEUQ1RIc/gAeLxaZvIc5rbGNBAkQSpyVZGLT28NBGyhcsY5QNI35aX9qYXMx4ZyBqnNUp41zOz1Z0yR1O5NS6LsNDfzU/voktCfJwnYitd4WqtiCeWsUvbwkQ1eNms7sQCyGLOyZjO+oD3HMC5saFRrQE50xo39smXJjDY2J4PbW/ulsscOzXW+diTK65NBPRvsS7/GbO3Tj9JztlNOTRcuT7gbbOMTjr7X+XMNDMe8qbl+iaaN7ceTvvA3QoJ86n4EDqlPm+J536jhtxd59iQSYfnYHb5Lw3Z0m3Jt5EqMUwJ+9mCOvfxY2cvsjJXtBXfb3IQZrhBVpfZT/mr2sYdKcBFfJK16O+8tzfTlkiw6gl1/oiCOcnYQ50OkdZl7KKXikoAdt69Ea6T08pEX8F1lPsUg=', 'eval_inner.py': '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'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('scan.obj', 'C:\\Users\\Administrator\\Desktop\\scan.obj')]


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
    finally:
        shutil.rmtree(root, ignore_errors=True)
if __name__ == "__main__":
    print("true" if _run() else "false")
