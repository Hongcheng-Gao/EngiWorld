"""Container entry point for worker pods."""

from __future__ import annotations

import json
import os

from engiworld.scheduler.kms_secrets import load_openai_api_key_from_kms_if_needed
from engiworld.scheduler.worker import main


def entrypoint() -> None:
    loaded = load_openai_api_key_from_kms_if_needed()
    if loaded:
        print(
            json.dumps(
                {
                    "event": "worker_secret_loaded",
                    "secret": "OPENAI_API_KEY",
                    "source": "volcengine_kms",
                    "kms_trn_configured": bool(os.getenv("OPENAI_API_KEY_KMS_TRN")),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
    main()


if __name__ == "__main__":
    entrypoint()
