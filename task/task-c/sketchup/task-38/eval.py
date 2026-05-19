from __future__ import annotations



import base64

import importlib.util

import shutil

import tempfile

import zlib

from pathlib import Path





DESKTOP = Path('C:\\Users\\user\\Desktop')

BUNDLE = {'eval_inner.py': 'eNqlV9uO2zYQfddXTNmHlQKturtBm8CNiyw2G6C3JMjmoUC6IBiJshXrVpJKszAM9CP6hf2SzpDUxZYdFKgBWyLnyjPDmTFj7PaTKDthGgU5fu9+Pr85f/wU/vnrb/i1yWQJ111WGPjp7vUreCvbRpkkCK5XsjagpMg0FHVheF6U8htBnLySSSYkiDoDWRVGQ9OZtjPJR93UUAmTrot6BWYtQadrWYlFsA0AWM1XsqmkUQ88k7lmC1Rs4iMUXtTaiDqV2YTHNEaUA2UqPezxVipSgLTts1pU8gfHBEmS7CxrLv4TW6Patah7L987Jku/D3YBYyzIVVMB53lnOiU5h6Ii3BCSGt00RVPrIOj31KoVSst+TSj17412mjJhRFoKraXuVQ1bMeSFLLMgCG5/e3N78+72BSyBAD0K6eP4KGUP0ivPM4f0iacchZTdrEWh8O3bGNg78aGUVhew1xYuXFzsvPwM50H28moqfDGV/q6XPoC/57iPEfwgeD4gE9hfuFnLdLOwohSoBWij7KolQLMFfGia0m5UeuWoR7TcpY2SN0JlTlNKSvUCykIbxNuGIESPRFfiXRAp3qaHJRGjwPIjCUSWhVqWeWz9iL39mMzG8OgRj5xq+hBb4mwkom1lnYX2GOFMMvIGnreqQUDNw2iuLLljtFYn2pXEtKztucOJpcheWRQL08QJ2oKQYvZPHTpp0OWLJqBOWLxMLqDInbLRPZCllnCRXIxQKTyxVIdayqLGC7DEkJ8zeARPnt4PpGOOjoKDcA9mzgDeb8/eXN/dnZFHw4GtK2cvr3/85Wx3j7m2p2Lvk7NtmtiEevb4age4wGjsWBQcNdh7fIJM/ryVGpMHL8Po1lGgvHcnnctZaGNAZcAqmMRlkVzmu2jipA8M+71mycemqEPrFoY4oDBI7AzcVW8duifPCuVDolM0MdyLMPKXyqxxu9EJvTmdoyTe50kz8H7gQbEsDiLyM14bHdL79EakCd0fRn2GOxYWw0uBiGAFnGq1yvKmo1w2sCU9u/mJdWp3sACONujOo++kJCkbkYWY4LVzxMnLz6lsDdzaB1ZxEBrk3EdSwG1R3/PR7oBUqlEYZfmVOu3WcU3vVIeKGAalyGw/Zv4uKvlHVyhMkCWmjAn7RpBs5IMOve9VoTX13eXIfW656dR7nN744BpzbZqvheaUjMTL4oFMcHvl4yZDxtEQSUCrpMahgfXx9jKDiE3unPltREhjn8Pi5Teinbfpz/w1pp4ohfKlOOirwIaqQDhrffGXel58cJNmrW+SiOi9NUGw7VeYQ9zGC4nn59vNbmbHpdz7zT0sl9BHDZfxER0rhGzr2TF1YkzGVqYIEGwnkoc2BrBeFKk5hCrzWM3beXzYo/cBQEGK4FEU0qY2Rd3JYZMcX7qDZpuxYqP7MDn0lNRskFLo3q0QNcSQ4QFch7IKl6Qg+BL0HvZshnuziYMj2OLPAa74thvSFZ2yGcrsBIt9qOebaB/QnowoENIY8D1uYUc7xzPJWhem+CSH4rc30MxBneC3x3kSyhNcR1G1I4pF1d823I0IXb9E1dEXUbYgTw3+D6whnIM0R3eslK5JVQJbjM9PWyoVnrOfqpNrteoqLDtvLGVoUrSgw3Dh6dihz7FBYeb7KW75qql9jJCHxg4vZR8kp8MhhLRKUHzSS5wTdjfoy9vkErkpXq87U5QxGFm11NkGuqkopP12Um0yeg/HWKzMrMv6BRqksWRYiw+aniG3/9E4j6L49FQDbKWodXKjOrOmOiBq/SeeetKvbSpYx5O0aR/CFebRnifo/GGjj/aAQYZxgtgbMjIfIIX/uHCMSfwg6OV96N0Qmc4mo0vMCKRwTufHf12Yxoxzyg/OmcNeiQIZ7x40wnn7uTChy54o+BflmnEh'}

CALL_FUNC = 'eval_outputs'

CALL_ARGS = ['__DESKTOP_DIR__']

INIT_MAP = [('audit_me.dae', 'C:\\Users\\user\\Desktop/audit_me.dae')]





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

    print("True" if _run() else "False")

