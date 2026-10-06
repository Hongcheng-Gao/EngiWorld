"""Helpers for loading worker runtime secrets from Volcengine KMS."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass


OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_API_KEY_KMS_TRN_ENV = "OPENAI_API_KEY_KMS_TRN"
OPENAI_API_KEY_KMS_FORCE_ENV = "OPENAI_API_KEY_KMS_FORCE"
OPENAI_API_KEY_KMS_VERSION_ID_ENV = "OPENAI_API_KEY_KMS_VERSION_ID"
OPENAI_API_KEY_KMS_VERSION_NAME_ENV = "OPENAI_API_KEY_KMS_VERSION_NAME"
OPENAI_API_KEY_KMS_JSON_FIELD_ENV = "OPENAI_API_KEY_KMS_JSON_FIELD"

_PLACEHOLDER_SECRET_VALUES = {"", "CHANGE_ME", "changeme", "YOUR_API_KEY", "sk-123"}


@dataclass(frozen=True)
class KmsSecretRef:
    region: str
    account_id: str
    secret_name: str


def load_openai_api_key_from_kms_if_needed() -> bool:
    """Load OPENAI_API_KEY from Volcengine KMS when configured.

    Returns True when OPENAI_API_KEY was populated from KMS. Existing non-placeholder
    values are left untouched unless OPENAI_API_KEY_KMS_FORCE is truthy.
    """

    trn = os.getenv(OPENAI_API_KEY_KMS_TRN_ENV, "").strip()
    if not trn:
        return False

    existing = os.getenv(OPENAI_API_KEY_ENV, "")
    force = _bool_env(OPENAI_API_KEY_KMS_FORCE_ENV, default=False)
    if existing not in _PLACEHOLDER_SECRET_VALUES and not force:
        return False

    secret_ref = parse_kms_secret_trn(trn)
    secret_value = get_kms_secret_value(
        secret_ref,
        version_id=os.getenv(OPENAI_API_KEY_KMS_VERSION_ID_ENV) or None,
        version_name=os.getenv(OPENAI_API_KEY_KMS_VERSION_NAME_ENV) or None,
    )
    api_key = _extract_secret_value(
        secret_value,
        json_field=os.getenv(OPENAI_API_KEY_KMS_JSON_FIELD_ENV) or None,
    )
    if not api_key:
        raise RuntimeError(
            f"KMS secret {secret_ref.secret_name!r} returned an empty OPENAI_API_KEY value."
        )

    os.environ[OPENAI_API_KEY_ENV] = api_key
    return True


def parse_kms_secret_trn(trn: str) -> KmsSecretRef:
    parts = trn.split(":", 4)
    if len(parts) != 5 or parts[0] != "trn" or parts[1] != "kms":
        raise ValueError(
            "OPENAI_API_KEY_KMS_TRN must look like "
            "'trn:kms:<region>:<account_id>:secrets/<secret_name>'."
        )

    _, _, region, account_id, resource = parts
    prefix = "secrets/"
    if not region or not account_id or not resource.startswith(prefix):
        raise ValueError(
            "OPENAI_API_KEY_KMS_TRN must look like "
            "'trn:kms:<region>:<account_id>:secrets/<secret_name>'."
        )
    secret_name = resource[len(prefix) :]
    if not secret_name:
        raise ValueError("OPENAI_API_KEY_KMS_TRN is missing the KMS secret name.")
    return KmsSecretRef(region=region, account_id=account_id, secret_name=secret_name)


def get_kms_secret_value(
    secret_ref: KmsSecretRef,
    *,
    version_id: str | None = None,
    version_name: str | None = None,
) -> str:
    try:
        import volcenginesdkcore
        import volcenginesdkkms.models as kms_models
        from volcenginesdkkms.api.kms_api import KMSApi
    except ImportError as exc:
        raise ImportError(
            "volcengine-python-sdk is required to load OPENAI_API_KEY from KMS."
        ) from exc

    access_key_id = os.getenv("VOLCENGINE_ACCESS_KEY_ID")
    secret_access_key = os.getenv("VOLCENGINE_SECRET_ACCESS_KEY")
    if not access_key_id or not secret_access_key:
        raise EnvironmentError(
            "VOLCENGINE_ACCESS_KEY_ID and VOLCENGINE_SECRET_ACCESS_KEY are required "
            "to read OPENAI_API_KEY from KMS."
        )

    configuration = volcenginesdkcore.Configuration()
    configuration.ak = access_key_id
    configuration.sk = secret_access_key
    configuration.region = secret_ref.region
    configuration.client_side_validation = True
    volcenginesdkcore.Configuration.set_default(configuration)

    request = kms_models.GetSecretValueRequest(secret_name=secret_ref.secret_name)
    if version_id:
        request.version_id = version_id
    if version_name:
        request.version_name = version_name

    response = KMSApi().get_secret_value(request)
    secret_value = getattr(response, "secret_value", None)
    if secret_value is None:
        raise RuntimeError(
            f"KMS GetSecretValue returned no SecretValue for {secret_ref.secret_name!r}."
        )
    return str(secret_value)


def _extract_secret_value(secret_value: str, *, json_field: str | None) -> str:
    if not json_field:
        return secret_value.strip()

    try:
        payload = json.loads(secret_value)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{OPENAI_API_KEY_KMS_JSON_FIELD_ENV}={json_field!r} was set, "
            "but the KMS secret value is not JSON."
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError("KMS secret value JSON must be an object when using a JSON field.")
    value = payload.get(json_field)
    if value is None:
        raise KeyError(f"KMS secret JSON value does not contain field {json_field!r}.")
    return str(value).strip()


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value, got {raw!r}")
