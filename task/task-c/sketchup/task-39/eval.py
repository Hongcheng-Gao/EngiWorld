from __future__ import annotations



import base64

import importlib.util

import shutil

import tempfile

import zlib

from pathlib import Path





DESKTOP = Path('C:\\Users\\Administrator\\Desktop')

BUNDLE = {'eval_inner.py': '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', 'collada.py': 'eJztHF2P28bxXb+CZV8omyf7bCMPQhQEcNwiD7aL3KEoQAgCT1rdMaZIlaTsk1P/987Mfs1+UJJTpy+tgPjI3ZnZ+d7ZD2bbtbtktdoehkMnVquk2u3bbkjKpmmHcqjapp9MVNuuHB4mW4TflEO5rsu+F71GME0SYjjubd8N/K3Fu3In+n25FhLicVfPxNAJoaHe1GInmuEWm8o+eXNrBm4Ou/0R25r9ZDLZiG2yavqsa9thOp8k8Ku2Cb7NhvJ+1g9lN/SfquEhS39LFQD+OgEiNslv6TqdM/B9XQ1Z+iXNk+tp8XxZXM+XXyYBfJp+0UNv67Yc+mwQj3p4BVlQT/Y4TbZtlzwmVZMQVAJvaTpVQ02XmlDVxMlA++VEtlWzWSFAti87UF+e7MFMedL0eQIA5aEeFu/aRqgxmnYjkkUiYWeInGn4qVYlwVR9gmg4LL7PiAfVGOhUDcSlMEia0UNTDat+XdaCLEcjSkLYAzyRSYijdPbs2XqO7jXAX+xOLYOKvtQ19s3uBRhwJwbRAVh6PXueTqcoB9EFlsGTpSyi7kUC/ZqlTrn4Cjy7qx6z8rECrZXNfS1WG3Gv2MNWYK/Zz8q+7LryqOA26OMLaCZWvns1VQrudgAt2YPOumrK+n6GzYQ3ZWpGyEXyfPY8UCggiqPIXo2N8pgnxzz5DAMRd8+ImOQWuYd2DNZZV26qEkLFikQwa92/blWfbO91e181vP01tIPakqtkPXGZlPow3Bfmid4ekycJ/vc6eZqsc3o80usVsP4k6WXTZwVxlE2gjmXu0jkyOgrxaGgR6aOhc0WQcTqfDZ0rPdpnRufRNn22pCN0oIna1T/XDgR79G0ne6ba/eoWokH7HsbLSkAKzBMbKcoD30r3O+kRmC3WD1W9wYxRV/1gKbIcCBkPaBFcJPtdXS8NJDgoAS+SVHKYzh0lfCxrdBedDRVJTGYOGJCpRZMh9BSJXX/nksEf0HfjC6Ejcs460T+Ue1LCq2mMTAHWeLlMniyYDqNw1xfCvbgADq3zNvkR4U2fqJn+hg5isC4H8W1U+DLU4O0FDuLAS0Xl8HCtH6Soi6SAgQ4C/N+KTM4lm8G5kJHlqBZu4zogOn+Y/DdfKf8Nyg9BCw8g/zU9gPwvUH4cZ1S6m7h0NJF8I/FeheLp0YMJC5GKOdqPnl4unSnyrU40MNv3YtW3h24t+gyqsAeVabBICLJNe8Bw/O2LSSsSEU1vUGmeLus6S9dz2Z2yCR1/snVVbYCWfJbzdLVJrfykmhUFvQWTJcB6zjrZ9I+/cg1y9MBZgDOI9UNT/fMgVut2t2sbLCMUsEeDJuCBsQnkODus/jHDBeUP/tZtM1TNweaFHkxDRRbWcRpXCi+7qEpJp5YXCi3uK4wRz2O69lNvgrQvqmSeVDBPScJLMleFloKUcy8y8HLlWwA8zRXY1MnyRLFsNgSJL1AET5MfgjjTIwfeWUAP4DgZI0fw4jrW+MJvfIKtL+fLMKegNNBJ8sDoTr+FBn8tjBmXVEgqWBUHAOBGwkfRDZUXCio6mBcHcaDRRiNBA/ixoNtlNOi3SDwop2TwZ3yN7N3sDwPxQtlZU2d8EYTPlBrPYisXFbsSBlmn0+RPkNn+9v7m59uf379Lw6wUMIM/HvYBaZ0ocB1Toy/us/TPqZsO0ZpM/qWJcakvQz9PiqWLedeJ8sOI3WEsCIgDTsIZ6KUiS39ctwdYgjnmLqRfrQ+dzC/PbXGFwKRhiWYVsm/rI4lLdAuFO9dEnkpU67C6fSE7XGPa4IWZSY55BbXZ3FfSrNzvBSS9AkcvcC6jh8o8wLjXS3dCCAJh31W7aqg+XjArKCNgkrp0Opk4vr8r9xb5XAQSquVOGoYaiXtEF48rDPSsE1u+yJdZio9KfoNQftbz8pvUkZNoFDXugEDIdT29ascsBlOxn7QU29iK8pg4pRLdSB+U6Ab2sjIds0aFexXS0WvKQSk6Ao6jn+/bpk+/jKQUSxLDtrexgL9d+bhqt1tYkJuYMB7rpB/L9yX5RyebWLIwecj1fM0ETq4+juxEaZ/z6VWONKyAIfE4gjqKJ2uf35nMHLXBS2YbciWKVwyS7nVsZ1oJGji3cuh4mQazh6RxzsqmSmE8QsZw5iwIMSKG1TXuMDkks8zwJBmRtWLA8YrBoIco9wJmjfXJc//+5pfbN/9AhZo558vUXXhj8WVbHMEddi+r0xSK5lO9GoNzij6OygtOHnLwo1O6gjxnGTNqWG5l427gwMUtESBZc/hVgQ1MqAHALK/fv//lp9TucUSYncGcNmQfxHFRl7u7TZlUg9jN6V8oBKcOBlW2XopBnlfcaUJe7WDR0jSsE8IiwY6ug4ztO8gc/iLM4ZE15dQabFuuhScMDmOaC0lw5YqwnHAfsXsFOn+7IuL2Onoc7RnzTV+dbyFu1vN9Kifh1E9j5BC4MR6sDZAwrAxe4t6XXB2ElR60u+KxDmTjlJA+SvsBoG+7Q7iPgui/Wv5eRhjB313ZY3hKaZ4ChmY8Cv2x2jyu9i3agRCfumEfxcF0otFgHWS0FOfHCPUXWILHmSC2TXXq/4B57Ys4M+FQhR5/OQ03L/CHuvqQ23zA40WnIFSlaA470WHVa21yQo4h0NYJNSne0QGKD8tAhMGIQP6tKX9v9Sn346+uQxEBof0QZ5OiSg8Gw5/Qj/UlHJIp4JQGdOAykayQdjBn+8fUWd80ZtU64zwFCThGBpnrw/BFQU3XJcHrLYm4pseXRpyJeArBnq/NIQZIWpcGHbEpWMksw1TJ88MlET0eruuHQ4PhTk4ervXUTkwc1Sz8TmQsVAgPJhqvcLLWfzkraBN5US4Z0xxRzMoyUoY4dZ+IcXI+TQ9fQpDfFcXGsRm7TAJvXlRztLNBQNhQOuB4xJhcvaEL4woHeyNVhZnuHVpy6+0cMbvB3mvflz0s3/RePfut4prYOb1+28fWbvhzMtxerVeDHW7N7bdNACqYRuqZ0VoGf/9BCKvdeuXc3yvY8diJbpJx0f8f6lae/+1Q95eMNMq5xaLZI6OqWq4dboS3VJcetQhWOu5uFVuixhY8eYSk9DhOmJhm2OA9AS4grtu224ADLQpAIybwr9KHWh2CGuBp1lefxTJOQA5PZAL/8HhaYX0W8BV1Q0DKE4ODTH2u9pllLLc+EK1cNdNO3zK2b2E3OI336ha1vFSbixZwMpn8aK9a0b/J65935b3KQdVmjjlJ7p+Ww4N8iyDdHDoUQWERAUUo+RftnkSRSrzI1b34Se0JKxqaWAzlbblXwBJ3bonEwN9st2I9hLJsqu32AFNg0t79CgDg7cQjeQMer9OFpvVxLs/wlAgcqn+omqoRfX8KpNxUzT26CA3sgUSFGwQEXR3y25Q7Yd+ElEpJd0LBmuC7Vk8q/XF319aWFCx77wWQ0pAxKiwRSCIyWucYFDCpoxezZhlFQSeL0jntVhcWYOlAmDCMwEW4+6tod2LojueUZp1e0WViIWGXmtUYnRAAT9WwWmW9qLd5cq+AcrykQWrr+aU40jMAzjQcmFw/ugAGXd6UUs+QNArL0UlO6FIOnl6hrLm8iQOeS4x1FUzej7saYXzO6EBNIbs9SAj74I/boWnrCz/wGAgDQ0pJ4MHtVHxAr3py5Dsro8+/ouUQulmLZpxKj71SVYDURxWiYcKxejVY7x54yUDM5B92akUJsF/dHYGYGknB0DgM3p7ayhuZylXbbUXX7jikvpSgelev3799+/5d6ty11JhjNyvfOAwDcxOeeXt7QK3SK2vBuawRn0DwUpX2NBQv7HV3cHlDupvqVQcensyMDbl6YAhactUfXr1wENkVTe94Gq0iLcA2Pzgu7X+Q2+CdYrsF4pDRyip6eZ6sZquMG51kzMyA+rItHetMvRo8vPEhdT+uBj3jRRTBUUcVoU69pVn4RhBHJ12wyzikCE8Sl6pyGaMXzaZWsXPk3mMoatVR8tR74ObSDZ1bWidzLuS4bm9RvtbxYY62mjZTd3j70YzA3Bo3g8avPspjKDBuP5S0nZbiQQZMkXR8+tA29/hwV1dN4x+iulzRGE6/3U1CkzPgr5ReVUFcctWkx2bEjQ0UiGsBBy/qeOhg+E2AoswRmHkJxvPrdVu33Uk8ggijwRlyPBqU08tw4DgyU1mmgkwgMVFPyvelh1uCOYsC39k5JWsJKHA1AW97mKlhVBZLZzgAiczcFjS4ckNFhxrWuit5FdMvgU+5AK+RvUi0qFEm5VU0RdoCu7f0Ttk/gjNifTYUv7WPd9Nsl/kQIa5PV0HyFr6HbLL611sruKjnm8mdvrYKIXaiFrKprvRd4WGpu2Tx1zHHU6Y2WK6dGd55O1vgk3b+Rjbjcp6xGF8UqxxpudksTL5kd/BlgC3UX9vBQ2LB7GEhDF8L88Q7zWJxwc0QnVpmdftJdNnUfgCgVu5tXZebcrQGxhW8X/hiG060+DGWlUWgH725nVGZS5/08Duj7UCBKOgOLr6ySqAhf9bfU5lmdvt7Ef94Z+LyJaspd4+XV1i2MCV3w61bqrb0zrP5/IdqU/oCqK7uurIDZCIDDfQQvchoK0VL1S3V/XZcMAUFLdHS5aRXa1kCY1XnqWKLsIGi3GMxlWZuh/MvLBmdmp1YfAtSjKYUJhmu/UKDLbWKPPPJ0PHspxrHDMgWO2csqAhBi3yK2VD22DuCF63VQp2pobTS5Os0MpLWjHybSdXIF083fNXvXIpTzWP60QCXaMgQgzb9HNOSoUkDOiNEl6YBntoviGDaiGCDeKHRDwGuniEqKpzX2nDeXOFY2MxmhvBW0h6dIxx0x37EOyJLIQ5dHV7K82/lSfapeJOPGZM4d3WVJzEXcv1CO5tuCIKUkY9+/8T9qGDAS6ZtzynVBlXl51zbPuaWemvrEre01KBRI8b8EvvkaA75kz5JOMofI1jWHxVx14r67myArB0SISJe6Fwr/pqL0GRIM2rwYal3tsn2EvUeZabkyK3kOWMn4mFW/drFNNnAxRTt0L18hygU5JLvctpyAPcYoRTpXb8xHxP2oT8pXznjSbQbF/OcrfrEmF2NJgxno6rdROd9w5rdH3W9LpwUtxohfqZoBS0U3JJTdgT/WPUHCFPahTwjPQfFUOLvFymFI3hj/BHKoQpeP6vb5VY1v091tiaHSlfGHXZGP1Q9y3vCFTS+Q+lJpaVABw+FYJ+uE4QRI2CL5jBgfUzfCz0gcOPeWjaAEPwLTwCZ8EJYvX2/KJZhp9y8X1zyNXGIrPb2LSMuSJBkRkMn1Jne7edQl32krH+Xf6zMONR38igoxv3UnI6Yk1frj9QVuXfh3Pkz1c6JgTqxlf4rZRivT0ax9Y6yiSz9DUpQ+zIVGMST1dRJbegzHq4WTdbfChtXjakX4qNjt52DKmcr/pzGRoUnotEPAPjv5LWckXKf/+SHL/2A8Ya+LNnVaXl0WJjJ7nA9qUd4Fv1i1ejPrgPGrdfH+05dcaUTZH6A6RXSOK7aSSXQS7WPP3IDon/WBvg7aQf8BSU2PyH3uJVH5ZLbXLExwmrU6flRMtVZ7LjYo8NmCq8slzN8+GnDH1gr6FNQGNSpEk6V3vqMtIjOw5eWH7z2cAOF6UKrl457M/9YFzfD2ILM+18Fgbn3C/hvOpGKCwFoVG65BX+RwcF9ZsFfZDc1u6+myTYT+wv6N59MJ+ZDDQolnyt2VWHBnqeTfwNyC08g'}

CALL_FUNC = 'eval_outputs'

CALL_ARGS = ['__DESKTOP_DIR__']

INIT_MAP = [('naming_mess.dae', 'C:\\Users\\Administrator\\Desktop/naming_mess.dae')]





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

