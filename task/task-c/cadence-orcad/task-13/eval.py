from __future__ import annotations

import base64
import importlib.util
import shutil
import tempfile
import zlib
from pathlib import Path


DESKTOP = Path(r'C:\Users\Administrator\Desktop')
BUNDLE = {'eval_inner.py': 'eNqdWFlz27YWfuevwOVLyEaiLXVyp1XrZtzE3SbXzsSuO3dkDQcmIZkxBbIA6NhV9d97DhYS1OakfrBI4ODsyweGYcgeaJnUT2ReCaKovB+Ovp4QXvGy4IwKwqkqHhjJKsGZGD4VrMwJe1SCZqqoeBKGYTAX1ZKk6bxRjWBpSoplXQlFKOeVokglg8CufZQVd8+CmZM1VXdlceuOvYfXIPjl7MMZOdEvEbAuSmAcJ4LJqnxgUZzUVDCugp/eXZxepZpUhNPhy9nr6PXkJn+J/5Ob/Kv49d/4+zKGhekZm2kSfH8dBlenH34+u0qv4eyr5PhV8P708jL949fztxd/6MXj5Pj4m+Dt6dVp+r9fz9Mf/391dom0x8fHQRDkbE7SsqJ5hPpPtKbxJCDwV8zBf0rblbDHQioZ2R38EwzcxMl5xZleU+JpaxPdlCBzqbmD3TRPFbg9Yjyr8oIvTsJGzYffhHGsz7LHjNWKnOkf8DihkrAttqswTZkQlUjTcELmIYoBNYVkZE6LEqI3ISu2DtfWPr2ViuqTjFD4hEglYjL8gZRg1DQvMjWFlQGZg6pqNjPybssqu5cYEJbIuixUJMJLxWrkRpfkzeklROtGfhUOCDI1+qOMyR62wGo601SYopo9KbiVMx1NZp2dGQV9l0b2kqrsDmRHGG4QpunjziUjRyghzZFyHn4YXZ++m4BuN6vVh9HlzXqNikYrl2XrXXzGO/iMPT7jz+PzUDVqm9P1xe9XyOj6JoKnm/h5Pjb5IusKynNjqn4Y2wcjzEtK7byKq4I3rDMNgpLQumY8j3qUq94b/oUYVsipgisrOVmIqqmjURwPtqnBuZiAGN8ItTtMPPaIx88Qo8NaamPmPvp1+xa7si0Zj9DqmPznhIxfeQVECyiSa1o27AwLKJqH7LFmmWI50EFdMHBTrj0GeVs14ONVy2wd2iQ3VYhrtsBks1xSUfzFokMFoEtuc9XoVlMpoRtA2gCraKQrBFhhfSBHtIneSuQ+Na6ZkSFxjS8m30OH7XW9l2TEhqOx1bfhWMetHUGvleAueBp/BiS0isCCfYI1PSy6FXKkiV1zyaolNnHTXhaVSg+5YEA+UX6YpGtMsOrcI6rbki3dGdzouomNtxOtY44LraTtpj2dh+jdDAKsyLKQusdMCLAw4W55rY3CZrVjuA5nQdvJgNhSQbT+Kur2tGespwKoCwRTU2kzVBap3Hu/lJ3drnrnmopUImcCI7GhOvJ9gRQvZq3imrlbDOPDnQLNuWdP0NGrEq2JIl3iA8ym/8YDEuki9l51Lg7ImA2/jjfakE1Z1AlYYr5qVfA5Jj+ghMlW2W/au0WglTRO6FlLVsB3vcsfKK/vDL0SbrGOt1ZuYVzf+8Xi1LOZj4grhdZUN4AMzG+aF6Itc2Nft+FwkEfaISFNS7lMESgApXfsyJZggnPeKG7QHArfIhVsnr56SGCxR7pkVAIw2EPuthP12D+WU0X3iYA9Q7tQTmsN94ACWzUHqCMadRfuMgCOWJHPHt2noWAaZ55AD8POBA3qJ1pKBg2r0zbUWMf3+LorXMH+bAoB7R4z3bl+4Pl2sOG8ge+VfknjrHb8doDFTt8p2EPRDdjBvOljVCSIkDGNsdECiHMsN/LVTSDNMXCpAwwNknW2tPMQNwupsSo0DxIVwF4qyjOGtAOdrbFGFPCaLJiKPIQZ9/rnlg0hHPnEhNG84QhxKVRJGOxW1vPXTi0+S9aykYrcMvLb5cU5qW4/ggv3ybPZ1vrG5mrrmoXa55mF8h2zUF/qFz+RP8Mxrlno+wGc79LwwLVhQLQ28gQk1yXNWNgaFr6/rAtYMK7mHWswM/zt4kfy5uL8zbvf35693SI5bFfXYEheMakPl1V1D7P5nhHqbppGvMvrslocNBxToqutBEKg4HYoVSoBVZHvSf/6dlDBudefMLYNd0VWPhGYD2VJotV+YWty+6SYjA+q27vsuXkPsr2bVr91fFkMu1nUIog+8432+W+5A6/UDTUQsBPK+SimPahVyQ1ctci3xUz7L7KP2TOBazhWCGADe5vtp5K1eMm4knjBfczWh7qMk2ADYTR90pKM+kEPWyJChrYd+T6JAw8V6TFh4LIHlL0m0EsKmxjAFe9S0LcM8unt42eT1Npo6IxiO0g1fjE0C7Wxv+nr5zCkHS9HBQcAU+QGOz0HDQ1sRbjqaf2cJIPK2i6hsZkLqh9NEjm8tnYzlqw8OXBB7t2MfcdZAP2cKo6r0aiYz5mQmg8xfZqYPh3tku7DR63K7h5gPqqd2EsrhtxenbxYeWw36G3ot4/o8uvTQgr06fanwKYnwhf64AsHMnAc8IoPebOEO0Vm/cwASPXwjYXyVo/hth2I6eFa8O3hOATbYN7p8yVZYkTuzhW7F/cRU7xpzHYghp6n/7U1VqHWqC9KtNasLt32WeOGZnszPjiyvyNh8rEqeNRvbP0ou4MaTOOxK+F/RLK72R3L7s3+tKeTM72DB0fbyP3IG80waUB9JiG0Yf+LTui+w3Sfr+EcEzDbNjLC5Iq6Y33nmq/cRGm8tcEbG/iR7d5HJvJ0IRgjnwplWG2nngG3GgZ6YjzOs2AHUAggPimEdokf008gDGm6pAXHj7YmfPb7uljo2vfX5JO0sL4GRzuK5FQsGtTnPb4Jd2msE5rnKbV7kX/9sRRigeMNCA2EwHd7GC+lvXss7iXefcnOSBw8+mt23ixrGYkBjKIcpJ2MAWBwDUSozIriRN/BLMQAK/AupKJjTFVhALROr1jnHhnFwT+1xqUp', 'ground_truth/ref_5v.dat': 'eNrt2ntsU1UcB/A7lfgik5ePGRy3MlhhpvS23fPcE1faDhagwDo2IWSsbpdR6drZlj2IFZTnKI4NBptILBQHIxtvs2T3ciBTFijbEAyTTWIIKCjRwFCY6MR52suiwv4AE3PvH+ckt99fT35tf2nzSZv09PeH12/pKY9T4XURXzaoLlXft6ipD2wa06hFg3Wa79/UJKVRjsE6LQ90pqkp92Cd+vs3tep4yjhY54xBh6furQMRFKW32w1OO8RP6rDiwg0ZJlTay9w2NzQaaEsJxxWFdjKcJf8YhqEMNpfZWsjBibTZ6bDbHJzVRcer1PF0Fu1etMThoV3cQs7FOfI4uszG2fNpj9W9WBV6mGXJm9Di4YroIqvLWkgb9BYTDWm8mNANTRmchUV2rhQylNHqsWaWFXF4PFzi0E3SJE7SJFBGW0F4WHWo+vdkasrkyA9PDdWPtBgNNSs0EAOzDAax1EBqlstZkG6ECYyO0VIZXLHZCTXxKkaFPy+P1eURXwg/NFzMcOZzeOxMrrAIahKpTBt+fzSaFEabolNThiWu8MYjT2Ue+Lys+ArNlqWcOSdzAg58ZwKVPhAZ02fqjeFicrreEiqMGaa0CVS22JA90JA90JB9r8Ey8AKjBgpKmaofKHX48h7akUpRqXp2a6swZmkjwAkan0vn92qr0ejL3ezmmjg46k8v6CeCJBWkIYJkKmj+aVFQ8XutwtgRewBOUFuZx7+kqEZ5zZ1spT0O5nZuIIIkFqQlgmQqaMNVUdAvi1uFKcE6gBPs13r53mHV6NTBsyyYEgd9iu1EkMSCdESQTAVd7BMFRcxtFbwfBwBO0HZ3Hd/yWDXKbutgc8bHwebv9hNBEguKJ4JkKuhCZCAsSDG1Vait9AOc4OveLXxU7ya0asgp9uWn4+BNxTEiSGJBCUSQTAWlVYjfQdzBFuFdSyPACX6/M5EfaqpClcu72UszlDC+LZsIklhQIhEkU0HKfaKgwOYWwdtTD3ACd7KJT1ZXoXn5neyuV5Rwa3QZESSxoCQiSKaCnEFR0CVvi+BpqAM4wfKGHN4WXYVyF55lC27FwuHN64kgiQUlE0EyFaS6JArS2VqEQysCACfom17Cfx9Zhdav6WBXnomFN3O3/S0o+X8VZHpYQaa0hxak+y+C9stLEKMmgOQJaGyvCOh2VoswudQPcAK6cg2fFFGFrp0IshcOxMJf1zQQQBIDYgggeQJq4URAhltIMCkbAU6wgIvktSUVaMXIbjbttXHw0/VaAkhiQBoCSJ6A2teJgHafQ4KvrR7gBG0WJe9dUIEin+xkZ9+OgT85MwkgiQFpCSB5AvpxjwgoikeCylcHcAJzuZ7fNK0CfTnqLKs6EQP9Tg8BJDEgHQEkT0A7jouAzDuR8FRBAOAES/+Yyy9NqUDDX+9gP/THwMRj5QSQxIDiCSB5Auq5IAJ6awMSinP8ACcwN7zNV8ZVoF2rg+wIbwyc315LAEkMKIEAkukfQYkioFVWXvimtwHgBJf3XW2OCfpQ35YutkbzKuwxDSeAJAaUSADJE1B2nggoyPLC7EA9wAn6uofyNXt96Bn/OXbfzwq4rIYhgCQGlEQAyRNQ7hoR0CfRvPBFQR3ACb76bBzft8WH3hfOsKajCmhVzSaAJAaUTADJE9DxOhFQ4hBeGDo1AHCCYXchf22FDwV72tkXNyrgvOtOAkhaQBpyEkGmgK4fEwFl3mgWvp3sBzjB6OVz+GVuH7qRGmRH2hVw55XVBJDEgMhJBJkCukuJgLbfaRKCRxoATjDt6OHm0pRydPKJLvaidQxEL1xOIYCkBUROIsgUkC1BBNTW3iTkuOsBThC17UpzbVQ5alKeY33Pj4F3aoaRbyCJAZGTCHL9CZcrAvphT5NQlFoHcILTGc/yjv61iHnjDHu+KxrW755EAEkMiJxEkCmgiJUiIPqDJiF2fADgBNNMY/mua2tRwkftbMeuaLhuiJkAkhgQOYkgU0CHd4iAPvc0CdHj/AAnaNqYwm88vxYduX2SLX4nGoLaxeAv9L4psw==', 'ground_truth/ref_5v.out': 'eNrNVd+PmkwUfTf1fzhJHz61lp0ZQd0mPiDQhMZfASRp36hOK98qbADbNJv+770DzLpuNulLm3RixuOdM+fOPVzGbmdAA8y8EZMbMYYQ7/jonckwqOOb8D7dSQjL4AZDT1hYJsXuAMHEuF9z4Luv0dJpdDvdDgZY5dkxzWRSwDKYhRjl4ZxVKOQXWciMFH+k8rhHlZR3htqiNikxNRw/cLZ+BNcLncDfRP561VAGf3Q0mqSK4JyhOkhkSZV+k7rmvdzdDXEn5X29WKan8zGp8uK/EkZ+rm6MfULTSSbluZBKJimq9Euyq8ohkmyPXa4qPuTfcUqyHygreX8vVbjIZFE2wnFvvY36+J5WhzRTGsotRna9uXkLZjA2RVz7Y2zswF7CsUMPM/DHQMBD+v0Q2fOF11Orw27nDfiQGbfjISA0GGlgamA1QNHHCk4pNtFgqsFtCzhrANE5H1IvMIoJDUYamBpYDVD0sYKCYhMNphrctkCwBhBd1OomxYQGIw1MDWp1s//zYoP4vQ3T2obmfDDbzGikLjaMr21o6fqgnD3SuVbnWv2ZDULbYLY2tHStzrX6MxvM1oaGLrS60OpCqz+xoduJHQdQE4Pr0Jm6nWDu22Edoh7DAxeMDahdiO0G3nsQUcXdT1ZM7RQs1rZbBxhRmaIKRTWWa9dbNCy46M3jGV0F8NX3CUE4E1jNuDHp101KmVU+LuoPBcLI2+BJ6y78MAKHwAgmLIwxwRS3ZCs4r/eMyDyyDXxMRpFFZA7ZAkF7BFlAxVPZ6lge1UbpAh7bizbDQ1PdZU08XRNXa7Eq9b2/cvUraEczZZqxCdZzry7GW7ndzqvuv3c/umm+l2geTF2dF3lB+DevSMp+PZp+uIynBD+kiavLSw3vLT3Nq/0rNVHLvLx7HqtZ9dhLy75e1uJsdLU7ULmpva6O9ryCD+s5nPXKWWxd7x99xOqIYWRH9Lr4Tohwu1zawcdnf5PbIPBWEep37KVx9ZdBrlgXO/5OmwBRXiVH/J9/RpWeJHrnMs2+IsyP32QB3qf8s8fjGSNG5v8C7ZO8Hw==', 'ground_truth/ref_5v_measure.txt': 'eNql1T1LxEAQgOHaQP7DlMphmJn9zEGKIOkE4XKmv8JSOMRO/O9+VprMzs5VKTbkIbtvJvPr0xnOp5fTM9yN8wQDELTN1YGW8X4Pbwea3weAvouION0iwfcq/67y2ury8Hjcw3L9ebkZIHQYHE47RBiPQB1/3bpDapu2mf/hbMCzjEevxV01Th3+PBE38F6NewvOEh5Zve3BgnsR906Lx1U8XxCcz1GLJwNeCI6DFs/VeDG4kLV4b8HF4EJOWpzQosvFkbo4Wptxf7a2Njmnf3c26LkQPKt1V60Xo9MPGvIWXa4u6M89WHQvN09qPa7rbK/OZf3OJ4NeqM6p/26Uq/VSdT6pRx31Fl2ujtRTntGiy9V59bThjVnnL6iO1OfObNDl6lzq1bqr1ovVOfX3zt6is9y8fueDRZero41p8wEMt68A', 'ground_truth/yield.json': 'eNqr5uVSUFAqKs0rVrJSMDLVAXMLEouLM/PSgSKGZhCRyszUnBQg30DPzISXq5aXCwB5eAzI'}
CALL_FUNC = 'eval_outputs'
CALL_ARGS = ['__DESKTOP_DIR__']
INIT_MAP = [('ref_5v.cir', r'C:\Users\Administrator\Desktop\ref_5v.cir')]


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
