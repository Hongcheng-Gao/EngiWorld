#!/usr/bin/env python3
"""Create an atomic, permission-restricted runtime API configuration file."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build the JSON file watched by OpenAI-compatible evaluation agents. "
            "The API key is read from a protected file and is never accepted as a "
            "command-line value."
        )
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-key-file", required=True, type=Path)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    base_url = args.base_url.strip().rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SystemExit("--base-url must be an absolute HTTP(S) URL")

    api_key = args.api_key_file.read_text(encoding="utf-8").strip()
    if not api_key:
        raise SystemExit("--api-key-file is empty")

    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "base_url": base_url,
        "api_key": api_key,
        "generation": secrets.token_hex(8),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.",
        suffix=".tmp",
        dir=output.parent,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, output)
        os.chmod(output, 0o600)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass

    print(
        json.dumps(
            {
                "output": str(output),
                "base_url": base_url,
                "generation": payload["generation"],
                "mode": "0600",
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
