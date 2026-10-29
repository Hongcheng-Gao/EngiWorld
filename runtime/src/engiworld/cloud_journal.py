"""Durable, credential-free records of paid cloud requests and their outcomes."""
from __future__ import annotations

import json
import uuid
from pathlib import Path


class CloudJournal:
    def __init__(self, root: Path, provider: str, **metadata):
        self.path = Path(root) / (uuid.uuid4().hex + ".json")
        self.data = dict(provider=provider, client_token=uuid.uuid4().hex,
                         instance_ids=[], state="intent", **metadata)
        self.update()

    def update(self, **values):
        self.data.update(values)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(self.data, stream, indent=2)
            stream.flush()
            import os
            os.fsync(stream.fileno())
        temporary.replace(self.path)


def cleanup_journals(ecs, root: Path, *, paths=None):
    """Reconcile lost responses; never infer absence after an uncertain create."""
    failures = []
    for path in paths if paths is not None else Path(root).rglob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("state") == "released":
            continue
        try:
            expected = ecs.provider_name
            if data["provider"] != expected or data["region"] != ecs.config.region:
                raise ValueError("Journal provider/region does not match the configured cloud")
            ids = data.get("instance_ids", [])
            if not ids and data.get("state") != "intent":
                ids = [i.instance_id for i in ecs.list_instances(instance_name=data["instance_name"])]
                if not ids:
                    raise RuntimeError("Creation outcome unknown; reconcile this request again")
            if ids:
                ecs.terminate_instances(ids)
            data.update(state="released", instance_ids=ids, cleanup_error=None)
        except Exception as exc:
            data.update(cleanup_error=str(exc))
            failures.append({"journal": str(path), **data})
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
        temporary.replace(path)
    return failures
