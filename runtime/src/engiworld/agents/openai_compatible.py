"""Shared OpenAI-compatible transport for OSWorld screenshot agents."""

from __future__ import annotations

import copy
import hashlib
import http.client
import json
import random
import logging
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from engiworld.scheduler.schemas import AgentConfig
from engiworld.active_time import task_paused


_LOGGER = logging.getLogger(__name__)
DEFAULT_MAX_TOKENS = 16384
_DISABLED_VALUES = {"", "0", "false", "none", "off", "disabled"}
_REASONING_ONLY_RETRY_PROMPT = (
    "Your previous response contained reasoning but no executable final action. "
    "Return the next action in the exact format required by the system prompt. "
    "Do not return reasoning only."
)


class OpenAICompatibleAPIError(RuntimeError):
    """Raised when an OpenAI-compatible model request cannot be completed."""


@dataclass(frozen=True)
class OpenAICompatibleEndpoint:
    """One resolved gateway endpoint without exposing its credential in logs."""

    base_url: str
    api_key: str
    revision: str


@dataclass(frozen=True)
class OpenAICompatibleAgentSpec:
    """Configuration for the shared OpenAI-compatible adapter."""

    display_name: str
    default_model: str
    default_base_url: str
    api_key_env: str
    env_prefix: str
    default_reasoning_effort: str | None = None
    default_reasoning_field: str = "reasoning_effort"
    ensure_final_user_turn: bool = False
    retry_reasoning_only_response: bool = False
    retry_empty_response: bool = True
    retry_stream_errors: bool = True
    retry_backoff_seconds: float = 0.0
    max_tokens_field: str = "max_tokens"


def create_agent(agent_config: AgentConfig) -> Any:
    """One factory for any OpenAI-compatible model; no provider-specific code."""
    spec = OpenAICompatibleAgentSpec(
        display_name="OpenAI-compatible model",
        default_model=agent_config.name,
        default_base_url=os.getenv("OPENAI_BASE_URL")
        or os.getenv("ARENA_MODEL_API_BASE_URL")
        or "https://api.example.invalid/v1",
        api_key_env="OPENAI_API_KEY",
        env_prefix="ARENA_MODEL",
        ensure_final_user_turn=_bool_env("ARENA_MODEL_ENSURE_FINAL_USER_TURN", False),
        max_tokens_field=_text_env("ARENA_MODEL_TOKEN_LIMIT_FIELD", "max_tokens"),
    )
    return create_prompt_agent(agent_config, spec)


def create_prompt_agent(agent_config: AgentConfig, spec: OpenAICompatibleAgentSpec) -> Any:
    """Create a PromptAgent with the shared transport and retry policy."""

    if agent_config.eval_mode == "auto":
        raise ValueError("AgentConfig.eval_mode must be resolved before creating the agent")

    try:
        from mm_agents.agent import PromptAgent
        from mm_agents.errors import ModelAPIError
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            f"{spec.display_name} requires OSWorld agent dependencies. "
            'Install them in the worker environment with `pip install -e ".[worker-api]"`. '
            f"Missing module: {exc.name!r}."
        ) from exc

    model = _text_env(f"{spec.env_prefix}_NAME", spec.default_model)
    base_url = _text_env(f"{spec.env_prefix}_BASE_URL", spec.default_base_url)
    reasoning_effort = _optional_env(
        f"{spec.env_prefix}_REASONING_EFFORT",
        spec.default_reasoning_effort,
    )
    reasoning_field = _reasoning_field(
        f"{spec.env_prefix}_REASONING_FIELD",
        spec.default_reasoning_field,
    )
    timeout_seconds = _float_env(f"{spec.env_prefix}_TIMEOUT_SECONDS", 600.0)
    api_retries = _int_env(
        f"{spec.env_prefix}_API_RETRIES",
        _int_env("OSWORLD_MODEL_API_MAX_RETRIES", 3),
    )
    stream = _bool_env(f"{spec.env_prefix}_STREAM", True)
    endpoint_provider = _runtime_endpoint_provider(spec, fallback_base_url=base_url)
    hot_swap_wait_seconds = _float_env(
        "ARENA_OPENAI_COMPAT_HOTSWAP_WAIT_SECONDS",
        86400.0 if endpoint_provider is not None else 0.0,
    )
    hot_swap_poll_seconds = _float_env(
        "ARENA_OPENAI_COMPAT_HOTSWAP_POLL_SECONDS",
        5.0,
    )

    class ArenaOpenAICompatiblePromptAgent(PromptAgent):
        _last_llm_exception: Exception | None = None

        def call_llm(self, payload):
            self._last_llm_exception = None
            self._llm_attempts = []
            try:
                endpoint = (
                    endpoint_provider()
                    if endpoint_provider is not None
                    else OpenAICompatibleEndpoint(
                        base_url=base_url,
                        api_key=require_api_key(
                            spec.api_key_env,
                            spec.display_name,
                            fallback_env="OPENAI_API_KEY",
                        ),
                        revision="environment",
                    )
                )
                return call_chat_completions(
                    payload,
                    base_url=endpoint.base_url,
                    api_key=endpoint.api_key,
                    provider_name=spec.display_name,
                    reasoning_effort=reasoning_effort,
                    reasoning_field=reasoning_field,
                    max_tokens_field=spec.max_tokens_field,
                    ensure_final_user_turn=spec.ensure_final_user_turn,
                    retry_reasoning_only_response=spec.retry_reasoning_only_response,
                    retry_empty_response=spec.retry_empty_response,
                    retry_stream_errors=spec.retry_stream_errors,
                    retry_backoff_seconds=spec.retry_backoff_seconds,
                    timeout_seconds=timeout_seconds,
                    retries=api_retries,
                    attempt_log=self._llm_attempts,
                    endpoint_provider=endpoint_provider,
                    hot_swap_wait_seconds=hot_swap_wait_seconds,
                    hot_swap_poll_seconds=hot_swap_poll_seconds,
                    stream=stream,
                )
            except Exception as exc:
                if isinstance(exc, ModelAPIError):
                    model_error = exc
                else:
                    model_error = ModelAPIError(
                        str(exc),
                        provider="openai_compatible",
                        attempts=max(1, len(self._llm_attempts)),
                    )
                self._last_llm_exception = model_error
                raise model_error from exc

        def predict(self, instruction: str, obs: dict[str, Any]):
            response, actions = super().predict(instruction, obs)
            if not actions and self._last_llm_exception is not None:
                raise self._last_llm_exception
            return response, actions

    return ArenaOpenAICompatiblePromptAgent(
        eval_mode=agent_config.eval_mode,
        experiment_profile=agent_config.experiment_profile,
        platform=os.getenv(f"{spec.env_prefix}_PLATFORM") or agent_config.platform or "ubuntu",
        model=model,
        max_tokens=_int_env(f"{spec.env_prefix}_MAX_TOKENS", DEFAULT_MAX_TOKENS),
        top_p=_optional_float_env(f"{spec.env_prefix}_TOP_P", None),
        temperature=_optional_float_env(f"{spec.env_prefix}_TEMPERATURE", None),
        action_space=agent_config.action_space,
        observation_type=agent_config.observation_type,
        max_trajectory_length=_int_env(
            f"{spec.env_prefix}_HISTORY_N", agent_config.history_turns or 3
        ),
        max_steps=agent_config.max_steps,
        wait_seconds=120.0,
        action_timeout_seconds=agent_config.bash_timeout,
        post_action_delay_seconds=agent_config.sleep_after_execution,
        screen_width=agent_config.screen_width,
        screen_height=agent_config.screen_height,
        client_password=agent_config.client_password or "",
        max_retries=api_retries,
        request_timeout=timeout_seconds,
        reasoning_effort=None,
    )


def call_chat_completions(
    payload: dict[str, Any],
    *,
    base_url: str,
    api_key: str,
    provider_name: str,
    reasoning_effort: str | None,
    reasoning_field: str = "reasoning_effort",
    max_tokens_field: str = "max_tokens",
    ensure_final_user_turn: bool = False,
    retry_reasoning_only_response: bool = False,
    retry_empty_response: bool = True,
    retry_stream_errors: bool = True,
    retry_backoff_seconds: float = 0.0,
    timeout_seconds: float = 180.0,
    retries: int = 1,
    attempt_log: list[dict[str, Any]] | None = None,
    endpoint_provider: Callable[[], OpenAICompatibleEndpoint] | None = None,
    hot_swap_wait_seconds: float = 0.0,
    hot_swap_poll_seconds: float = 5.0,
    stream: bool = False,
) -> str:
    """Call an OpenAI-compatible chat/completions endpoint with vision content."""

    if retries < 1:
        raise ValueError("retries must be at least 1")
    if hot_swap_wait_seconds < 0:
        raise ValueError("hot_swap_wait_seconds cannot be negative")
    if hot_swap_poll_seconds <= 0:
        raise ValueError("hot_swap_poll_seconds must be greater than zero")
    request_payload = prepare_payload(
        payload,
        reasoning_effort=reasoning_effort,
        reasoning_field=reasoning_field,
        max_tokens_field=max_tokens_field,
    )
    if ensure_final_user_turn:
        _ensure_final_user_turn(
            request_payload.get("messages"),
            provider_name=provider_name,
        )
    last_error = "request was not attempted"
    attempts_made = 0
    reasoning_retry_prompt_added = False
    endpoint = OpenAICompatibleEndpoint(
        base_url=base_url,
        api_key=api_key,
        revision="initial",
    )
    if stream:
        request_payload["stream"] = True
    if endpoint_provider is not None:
        endpoint = endpoint_provider()

    while True:
        api_url = chat_completions_url(endpoint.base_url)
        headers = {
            "Authorization": f"Bearer {endpoint.api_key}",
            "Content-Type": "application/json",
        }
        hot_swap_eligible = False

        if api_url.startswith("http://"):
            _LOGGER.warning(
                "%s uses insecure HTTP; API credentials and screenshots are not "
                "encrypted in transit",
                provider_name,
            )

        for attempt in range(1, retries + 1):
            attempts_made += 1
            started_at = time.monotonic()
            try:
                post = _post_stream_json if stream else _post_json
                status_code, response_text = post(
                    api_url,
                    headers=headers,
                    payload=request_payload,
                    timeout=timeout_seconds,
                )
                latency_ms = int((time.monotonic() - started_at) * 1000)
                if status_code == 200:
                    response_payload = json.loads(response_text)
                    if not isinstance(response_payload, dict):
                        raise ValueError("Chat response must be a JSON object")
                    upstream_error = _response_upstream_error(response_payload)
                    stream_error = _response_stream_error(response_payload)
                    if upstream_error or stream_error:
                        # Validation is mandatory even when retries are disabled.
                        status = "upstream_error" if upstream_error else "stream_incomplete"
                        last_error = f"{provider_name} {status}: {upstream_error or stream_error}"
                        _append_attempt(
                            attempt_log,
                            status=status,
                            model=str(request_payload.get("model") or ""),
                            http_status=200,
                            latency_ms=latency_ms,
                            usage=response_payload.get("usage"),
                            error=last_error,
                            raw_finish_reason=_first_finish_reason(response_payload),
                        )
                        if attempt_log:
                            attempt_log[-1]["retry_policy"] = f"{status.replace('_', '-')}-identical-request-v1"
                        if retry_stream_errors and attempt < retries:
                            _LOGGER.warning("%s; retrying the identical request", last_error)
                            _sleep_before_retry(attempt, retry_backoff_seconds, attempt_log)
                            continue
                        break
                    content = extract_chat_content(response_payload)
                    if not content:
                        reasoning_content = extract_chat_reasoning(response_payload)
                        if retry_empty_response:
                            # Repeat the identical request: no corrective prompt or reasoning replay.
                            finish_reason = _first_finish_reason(response_payload)
                            last_error = (
                                f"{provider_name} returned empty assistant content "
                                f"(reasoning_chars={len(reasoning_content or '')}, "
                                f"finish_reason={finish_reason!r})"
                            )
                            _append_attempt(
                                attempt_log,
                                status="reasoning_only" if reasoning_content else "empty_response",
                                model=str(request_payload.get("model") or ""),
                                http_status=200,
                                latency_ms=latency_ms,
                                usage=response_payload.get("usage"),
                                error=last_error,
                                raw_finish_reason=finish_reason,
                            )
                            if attempt_log:
                                attempt_log[-1]["retry_policy"] = "empty-response-identical-request-v1"
                            if attempt < retries:
                                _LOGGER.warning("%s; retrying the identical request", last_error)
                                _sleep_before_retry(attempt, retry_backoff_seconds, attempt_log)
                                continue
                            break
                        if retry_reasoning_only_response and reasoning_content:
                            finish_reason = _first_finish_reason(response_payload)
                            last_error = (
                                f"{provider_name} returned reasoning_content "
                                f"({len(reasoning_content)} chars) but no assistant content"
                            )
                            _append_attempt(
                                attempt_log,
                                status="reasoning_only",
                                model=str(request_payload.get("model") or ""),
                                http_status=200,
                                latency_ms=latency_ms,
                                usage=response_payload.get("usage"),
                                error=last_error,
                                raw_finish_reason=finish_reason,
                            )
                            _LOGGER.warning("%s; retrying for a final action", last_error)
                            if attempt < retries:
                                if not reasoning_retry_prompt_added:
                                    _append_reasoning_only_retry_prompt(
                                        request_payload.get("messages")
                                    )
                                    reasoning_retry_prompt_added = True
                                _sleep_before_retry(attempt, retry_backoff_seconds, attempt_log)
                                continue
                            break
                        raise OpenAICompatibleAPIError(
                            f"{provider_name} returned an empty assistant message: "
                            f"{_compact_payload(response_payload)}"
                        )
                    _append_attempt(
                        attempt_log,
                        status="ok",
                        model=str(request_payload.get("model") or ""),
                        http_status=200,
                        latency_ms=latency_ms,
                        usage=response_payload.get("usage"),
                    )
                    return content

                last_error = f"HTTP {status_code}: {response_text[:2000]}"
                _append_attempt(
                    attempt_log,
                    status="http_error",
                    model=str(request_payload.get("model") or ""),
                    http_status=status_code,
                    latency_ms=latency_ms,
                    error=last_error,
                )
                _LOGGER.error("%s API call failed: %s", provider_name, last_error)
                context_limit = _is_context_limit_error(response_text)
                if context_limit:
                    request_payload["messages"] = _shortened_messages(
                        request_payload.get("messages")
                    )
                hot_swap_eligible = _is_hot_swappable_http_status(status_code)
                if not context_limit and status_code in {400, 401, 403, 404}:
                    break
            except (OSError, ValueError, http.client.HTTPException) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                hot_swap_eligible = True
                _append_attempt(
                    attempt_log,
                    status="exception",
                    model=str(request_payload.get("model") or ""),
                    http_status=None,
                    latency_ms=int((time.monotonic() - started_at) * 1000),
                    error=last_error,
                )
                _LOGGER.error("%s API call raised: %s", provider_name, last_error)

            if attempt < retries:
                _sleep_before_retry(attempt, retry_backoff_seconds, attempt_log)

        if not (
            hot_swap_eligible
            and endpoint_provider is not None
            and hot_swap_wait_seconds > 0
        ):
            break
        replacement = _wait_for_endpoint_change(
            endpoint_provider,
            previous_revision=endpoint.revision,
            provider_name=provider_name,
            wait_seconds=hot_swap_wait_seconds,
            poll_seconds=hot_swap_poll_seconds,
        )
        if replacement is None:
            break
        endpoint = replacement
        _LOGGER.info(
            "%s runtime API configuration changed; retrying the same model step",
            provider_name,
        )

    raise OpenAICompatibleAPIError(
        f"{provider_name} API failed after {attempts_made} "
        f"attempt(s) at {api_url}: {last_error}"
    )


def _response_upstream_error(response_payload: dict[str, Any]) -> str | None:
    """Extract explicit errors from a reconstructed SSE response, not ordinary warnings."""
    errors = []
    if response_payload.get("error") is not None:
        errors.append(response_payload["error"])
    warnings = response_payload.get("stream_warnings") or []
    if not isinstance(warnings, list):
        warnings = [warnings]
    for warning in warnings:
        if isinstance(warning, str):
            try:
                warning = json.loads(warning.removeprefix("data:").strip())
            except ValueError:
                continue
        if isinstance(warning, dict) and warning.get("error") is not None:
            errors.append(warning["error"])
    return _compact_payload({"errors": errors}) if errors else None


def _response_stream_error(response_payload: dict[str, Any]) -> str | None:
    """Require a complete SSE response before allowing its content to execute."""
    state = response_payload.get("_stream_state")
    if state is None:  # A non-streaming JSON response.
        return None
    if state.get("malformed"):
        return "malformed SSE data"
    if not state.get("done"):
        return "SSE ended without [DONE]"
    if not _first_finish_reason(response_payload):
        return "SSE ended without finish_reason"
    return None


def _sleep_before_retry(attempt: int, base_seconds: float, attempt_log) -> None:
    """Use a linear delay by default or a configured exponential delay with jitter."""
    if base_seconds > 0:
        delay = min(base_seconds * (2 ** min(attempt - 1, 10)), 60.0)
        delay += random.uniform(0.0, base_seconds / 2.0)
    else:
        delay = min(1.5 * attempt, 15.0)
    if attempt_log:
        attempt_log[-1]["retry_wait_seconds"] = round(delay, 3)
    time.sleep(delay)


def prepare_payload(
    payload: dict[str, Any],
    *,
    reasoning_effort: str | None,
    reasoning_field: str,
    max_tokens_field: str = "max_tokens",
) -> dict[str, Any]:
    """Copy and normalize a PromptAgent payload for strict compatible gateways."""

    prepared = copy.deepcopy(payload)
    if max_tokens_field not in {"max_tokens", "max_completion_tokens"}:
        raise ValueError(f"Unsupported token limit field: {max_tokens_field!r}")
    if max_tokens_field == "max_completion_tokens" and "max_tokens" in prepared:
        # Preserve an explicit completion limit and send only the provider field.
        prepared.setdefault("max_completion_tokens", prepared.pop("max_tokens"))
    _strip_private_fields(prepared.get("messages"))
    if prepared.get("temperature") is None:
        prepared.pop("temperature", None)
    if prepared.get("top_p") is None:
        prepared.pop("top_p", None)

    prepared.pop("reasoning", None)
    prepared.pop("reasoning_effort", None)
    if reasoning_effort:
        if reasoning_field == "reasoning_effort":
            prepared["reasoning_effort"] = reasoning_effort
        elif reasoning_field == "reasoning":
            prepared["reasoning"] = {"effort": reasoning_effort}
        elif reasoning_field != "none":
            raise ValueError(f"Unsupported reasoning field {reasoning_field!r}")
    return prepared


def chat_completions_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if not normalized.startswith(("http://", "https://")):
        raise ValueError(f"Model base URL must start with http:// or https://, got {base_url!r}")
    if normalized.endswith("/v1"):
        return f"{normalized}/chat/completions"
    return f"{normalized}/v1/chat/completions"


def _runtime_endpoint_provider(
    spec: OpenAICompatibleAgentSpec,
    *,
    fallback_base_url: str,
) -> Callable[[], OpenAICompatibleEndpoint] | None:
    enabled = _bool_env("ARENA_OPENAI_COMPAT_HOTSWAP_ENABLED", False)
    explicit_path = (
        os.getenv(f"{spec.env_prefix}_RUNTIME_CONFIG_FILE", "").strip()
        or os.getenv("ARENA_OPENAI_COMPAT_RUNTIME_CONFIG_FILE", "").strip()
    )
    if not enabled and not explicit_path:
        return None

    if explicit_path:
        config_path = Path(explicit_path).expanduser()
    else:
        run_id = os.getenv("ARENA_RUN_ID", "").strip()
        if not run_id:
            raise EnvironmentError(
                "ARENA_RUN_ID is required when OpenAI-compatible API hot switching is enabled"
            )
        config_dir = Path(
            os.getenv(
                "ARENA_OPENAI_COMPAT_RUNTIME_CONFIG_DIR",
                "model-api",
            )
        ).expanduser()
        config_path = config_dir / f"{_safe_runtime_name(run_id)}.json"

    warning_revision: str | None = None

    def fallback_api_key() -> str:
        return require_api_key(
            spec.api_key_env,
            spec.display_name,
            fallback_env="OPENAI_API_KEY",
        )

    def resolve() -> OpenAICompatibleEndpoint:
        nonlocal warning_revision
        try:
            raw = config_path.read_bytes()
        except FileNotFoundError:
            return OpenAICompatibleEndpoint(
                base_url=fallback_base_url,
                api_key=fallback_api_key(),
                revision=f"missing:{config_path}",
            )
        except OSError as exc:
            revision = f"unreadable:{config_path}:{type(exc).__name__}"
            if revision != warning_revision:
                _LOGGER.warning(
                    "%s runtime API config is unreadable at %s: %s",
                    spec.display_name,
                    config_path,
                    exc,
                )
                warning_revision = revision
            return OpenAICompatibleEndpoint(
                base_url=fallback_base_url,
                api_key=fallback_api_key(),
                revision=revision,
            )

        digest = hashlib.sha256(raw).hexdigest()
        revision = f"file:{digest}"
        try:
            if os.name != "nt" and config_path.stat().st_mode & 0o077:
                raise PermissionError("file permissions must be 0600")
            config = json.loads(raw.decode("utf-8"))
            if not isinstance(config, dict):
                raise ValueError("top-level JSON value must be an object")
            resolved_base_url = str(config.get("base_url") or fallback_base_url).strip()
            resolved_api_key = str(config.get("api_key") or fallback_api_key()).strip()
            if not resolved_base_url or not resolved_api_key:
                raise ValueError("base_url and api_key must resolve to non-empty values")
            chat_completions_url(resolved_base_url)
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            invalid_revision = f"invalid:{digest}"
            if invalid_revision != warning_revision:
                _LOGGER.warning(
                    "%s runtime API config is invalid at %s: %s",
                    spec.display_name,
                    config_path,
                    exc,
                )
                warning_revision = invalid_revision
            return OpenAICompatibleEndpoint(
                base_url=fallback_base_url,
                api_key=fallback_api_key(),
                revision=invalid_revision,
            )

        warning_revision = None
        return OpenAICompatibleEndpoint(
            base_url=resolved_base_url,
            api_key=resolved_api_key,
            revision=revision,
        )

    return resolve


def _wait_for_endpoint_change(
    endpoint_provider: Callable[[], OpenAICompatibleEndpoint],
    *,
    previous_revision: str,
    provider_name: str,
    wait_seconds: float,
    poll_seconds: float,
) -> OpenAICompatibleEndpoint | None:
    deadline = time.monotonic() + wait_seconds
    _LOGGER.warning(
        "%s API is unavailable; preserving the current task state for up to %.0f seconds "
        "while waiting for a runtime API configuration update",
        provider_name,
        wait_seconds,
    )
    previous_phase = os.environ.get("ARENA_TASK_RUNTIME_PHASE")
    os.environ["ARENA_TASK_RUNTIME_PHASE"] = "api_hot_swap_waiting"
    try:
        with task_paused("api_hot_swap_waiting"):
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                time.sleep(min(poll_seconds, remaining))
                candidate = endpoint_provider()
                if candidate.revision != previous_revision:
                    return candidate
    finally:
        if previous_phase is None:
            os.environ.pop("ARENA_TASK_RUNTIME_PHASE", None)
        else:
            os.environ["ARENA_TASK_RUNTIME_PHASE"] = previous_phase


def _safe_runtime_name(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
    if not safe:
        safe = "run"
    if safe == value and len(safe) <= 180:
        return safe
    suffix = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"{safe[:160]}-{suffix}"


def _is_hot_swappable_http_status(status_code: int) -> bool:
    return status_code in {401, 403, 404, 408, 409, 425, 429} or status_code >= 500


def _ensure_final_user_turn(messages: Any, *, provider_name: str) -> None:
    """Append a user continuation when a strict provider sees a trailing model turn."""

    if not isinstance(messages, list):
        return

    roles = [
        str(message.get("role") or "")
        for message in messages
        if isinstance(message, dict)
    ]
    for message in reversed(messages):
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "").strip().lower()
        if role == "system":
            continue
        if role in {"assistant", "model"}:
            _LOGGER.warning(
                "%s request ended with role=%r; appending a user continuation; roles=%s",
                provider_name,
                role,
                roles,
            )
            messages.append({
                "role": "user",
                "content": [{
                    "type": "text",
                    "text": "Continue the task based on the latest available observation.",
                }],
            })
        return


def require_api_key(
    env_name: str,
    display_name: str,
    *,
    fallback_env: str | None = None,
) -> str:
    api_key = os.getenv(env_name, "").strip()
    if not api_key and fallback_env:
        api_key = os.getenv(fallback_env, "").strip()
    if not api_key:
        accepted = f"{env_name} or {fallback_env}" if fallback_env else env_name
        raise EnvironmentError(
            f"{accepted} must be set in the worker environment for {display_name}."
        )
    return api_key


def extract_chat_content(payload: dict[str, Any]) -> str | None:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first_choice = choices[0] if isinstance(choices[0], dict) else {}
    message = first_choice.get("message")
    message = message if isinstance(message, dict) else {}
    content = message.get("content")
    if isinstance(content, str):
        return content.strip() or None
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        joined = "\n".join(part.strip() for part in parts if part.strip())
        return joined or None
    text = first_choice.get("text")
    if isinstance(text, str):
        return text.strip() or None
    return None


def extract_chat_reasoning(payload: dict[str, Any]) -> str | None:
    """Extract non-executable reasoning text from a compatible response."""

    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first_choice = choices[0] if isinstance(choices[0], dict) else {}
    message = first_choice.get("message")
    message = message if isinstance(message, dict) else {}
    for field in ("reasoning_content", "reasoning"):
        value = message.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _first_finish_reason(payload: dict[str, Any]) -> str | None:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return None
    finish_reason = choices[0].get("finish_reason")
    return str(finish_reason) if finish_reason is not None else None


def _append_reasoning_only_retry_prompt(messages: Any) -> None:
    if not isinstance(messages, list):
        return
    messages.append(
        {
            "role": "user",
            "content": [{"type": "text", "text": _REASONING_ONLY_RETRY_PROMPT}],
        }
    )


def _strip_private_fields(messages: Any) -> None:
    if not isinstance(messages, list):
        return
    for message in messages:
        if not isinstance(message, dict):
            continue
        if str(message.get("role") or "").lower() in {"assistant", "model"}:
            for key in ("reasoning_content", "reasoning", "thinking", "thought"):
                message.pop(key, None)
        content = message.get("content")
        if not isinstance(content, list):
            continue
        message["content"] = [
            part
            for part in content
            if not (
                isinstance(part, dict)
                and (
                    str(part.get("type") or "").lower()
                    in {"reasoning", "thinking", "thought"}
                    or part.get("thought") is True
                )
            )
        ]
        for part in message["content"]:
            if not isinstance(part, dict):
                continue
            for key in list(part):
                if key.startswith("_"):
                    part.pop(key, None)
            source = part.get("source")
            if isinstance(source, dict):
                for key in list(source):
                    if key.startswith("_"):
                        source.pop(key, None)


def _shortened_messages(messages: Any) -> list[Any]:
    if not isinstance(messages, list) or len(messages) <= 2:
        return messages if isinstance(messages, list) else []
    return [messages[0], messages[-1]]


def _post_json(
    url: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: float,
) -> tuple[int, str]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status), response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read().decode("utf-8", errors="replace")


def _post_stream_json(
    url: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: float,
) -> tuple[int, str]:
    """Read an OpenAI-compatible SSE stream and rebuild one chat response."""

    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={**headers, "Accept": "text/event-stream"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status), _decode_sse_response(response)
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read().decode("utf-8", errors="replace")


def _decode_sse_response(lines: Any) -> str:
    content_parts: list[str] = []
    reasoning_parts: list[str] = []
    raw_lines: list[str] = []
    usage: Any = None
    finish_reason: str | None = None
    saw_sse = False
    saw_done = False
    malformed = False
    pending_data: str | None = None

    for raw_line in lines:
        if isinstance(raw_line, bytes):
            line = raw_line.decode("utf-8", errors="replace").strip()
        else:
            line = str(raw_line).strip()
        if not line:
            if pending_data is not None:
                raw_lines.append(pending_data)
                malformed = True
                pending_data = None
            continue
        if line.startswith(":"):
            continue
        if line.startswith(("event:", "id:", "retry:")):
            continue
        if not line.startswith("data:"):
            raw_lines.append(line)
            continue

        saw_sse = True
        data = line[5:].strip()
        if pending_data is not None:
            data = pending_data + "\n" + data
        if data == "[DONE]":
            saw_done = True
            break
        try:
            chunk = json.loads(data)
        except json.JSONDecodeError:
            # SSE permits a JSON event to span multiple data: lines. It must
            # parse before the event's blank separator or the end of the stream.
            pending_data = data
            continue
        pending_data = None
        if not isinstance(chunk, dict):
            malformed = True
            continue
        if chunk.get("usage") is not None:
            usage = chunk.get("usage")
        if chunk.get("error") is not None:
            raw_lines.append(json.dumps(chunk, ensure_ascii=False))
            continue
        choices = chunk.get("choices")
        if not isinstance(choices, list) or not choices:
            if "choices" in chunk and not isinstance(choices, list):
                malformed = True
            continue
        if not isinstance(choices[0], dict):
            malformed = True
            continue
        choice = choices[0]
        if choice.get("finish_reason") is not None:
            finish_reason = str(choice.get("finish_reason"))
        delta = choice.get("delta")
        if not isinstance(delta, dict):
            delta = choice.get("message") if isinstance(choice.get("message"), dict) else {}
        content_parts.extend(_stream_text_parts(delta.get("content")))
        if choice.get("text") is not None:
            content_parts.extend(_stream_text_parts(choice.get("text")))
        for field in ("reasoning_content", "reasoning"):
            reasoning_parts.extend(_stream_text_parts(delta.get(field)))

    if pending_data is not None:
        raw_lines.append(pending_data)
        malformed = True
    if not saw_sse:
        return "\n".join(raw_lines)

    message: dict[str, Any] = {"role": "assistant", "content": "".join(content_parts)}
    if reasoning_parts:
        message["reasoning_content"] = "".join(reasoning_parts)
    reconstructed: dict[str, Any] = {
        "choices": [{"finish_reason": finish_reason, "message": message}],
        "_stream_state": {"done": saw_done, "malformed": malformed},
    }
    if usage is not None:
        reconstructed["usage"] = usage
    if raw_lines:
        reconstructed["stream_warnings"] = raw_lines
    return json.dumps(reconstructed, ensure_ascii=False)


def _stream_text_parts(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        return []
    parts = []
    for item in value:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict) and isinstance(item.get("text"), str):
            parts.append(item["text"])
    return parts


def _is_context_limit_error(response_text: str) -> bool:
    try:
        payload = json.loads(response_text)
        error = payload.get("error") or {}
    except (ValueError, AttributeError):
        return False
    code = str(error.get("code") or "").lower()
    message = str(error.get("message") or "").lower()
    return code == "context_length_exceeded" or "context length" in message


def _append_attempt(
    attempt_log: list[dict[str, Any]] | None,
    *,
    status: str,
    model: str,
    http_status: int | None,
    latency_ms: int,
    usage: Any = None,
    error: str | None = None,
    raw_finish_reason: str | None = None,
) -> None:
    if attempt_log is None:
        return
    attempt_log.append(
        {
            "status": status,
            "provider": "openai_compatible",
            "model": model,
            "raw_finish_reason": raw_finish_reason,
            "http_status": http_status,
            "usage": usage,
            "latency_ms": latency_ms,
            "error": error,
        }
    )


def _reasoning_field(env_name: str, default: str) -> str:
    value = os.getenv(env_name, default).strip().lower()
    aliases = {"off": "none", "disabled": "none", "": "none"}
    value = aliases.get(value, value)
    if value not in {"reasoning_effort", "reasoning", "none"}:
        raise ValueError(
            f"{env_name} must be reasoning_effort, reasoning, or none; got {value!r}"
        )
    return value


def _text_env(name: str, default: str) -> str:
    value = os.getenv(name, default).strip()
    if not value:
        raise ValueError(f"{name} cannot be empty")
    return value


def _optional_env(name: str, default: str | None) -> str | None:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip()
    if value.lower() in _DISABLED_VALUES:
        return None
    return value


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {raw!r}") from exc


def _optional_float_env(name: str, default: float | None) -> float | None:
    raw = os.getenv(name)
    if raw is None:
        return default
    if raw.strip().lower() in _DISABLED_VALUES:
        return None
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number or 'none', got {raw!r}") from exc


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in _DISABLED_VALUES:
        return False
    raise ValueError(f"{name} must be a boolean value, got {raw!r}")


def _compact_payload(payload: dict[str, Any], limit: int = 1200) -> str:
    try:
        text = json.dumps(payload, ensure_ascii=False, default=str)
    except TypeError:
        text = str(payload)
    return text[:limit]
