"""Reconcile and release only instances owned by specified request journals."""
import argparse
import json
from pathlib import Path

from engiworld.cloud_journal import cleanup_journals
from engiworld.scheduler.cloud_factory import make_cloud_client


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", required=True, choices=["aliyun", "volcengine"])
    parser.add_argument("--journal-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    if not args.journal_dir.is_dir() or not list(args.journal_dir.rglob("*.json")):
        parser.error("Select an existing directory containing cloud request journals")
    client = make_cloud_client(args.provider, journal_dir=args.journal_dir)
    failures = cleanup_journals(client, args.journal_dir)
    print(json.dumps({"release_confirmed": not failures, "unresolved_requests": failures}, indent=2))
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
