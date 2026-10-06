import copy
import http.client
import json
import os
import sys
import types
from dataclasses import replace
from unittest.mock import patch

import pytest

from engiworld.agents import openai_compatible as transport
from engiworld.agents.profiles import (
    AGENT_PROFILES, MODEL_PRESETS, SHARED_AGENT_FACTORY, get_agent_profile,
)
from engiworld.scheduler.master import _parse_agent_env
from engiworld.scheduler.schemas import AgentConfig


@pytest.fixture
def fake_agent_module(monkeypatch):
    package = types.ModuleType("mm_agents")
    package.__path__ = []
    module = types.ModuleType("mm_agents.agent")
    errors = types.ModuleType("mm_agents.errors")

    class PromptAgent:
        def __init__(self, **kwargs):
            self.settings = kwargs

        def predict(self, instruction, obs):
            # Match the base agent's exception-swallowing behavior: the wrapper
            # must propagate model failures instead of returning an empty step.
            try:
                response = self.call_llm({"model": self.settings["model"], "messages": []})
            except Exception:
                return "", []
            return response, [response]

    class ModelAPIError(RuntimeError):
        def __init__(self, message, **kwargs):
            super().__init__(message)
            self.attempts = kwargs.get("attempts")

    module.PromptAgent = PromptAgent
    errors.ModelAPIError = ModelAPIError
    for name, value in {"mm_agents": package, "mm_agents.agent": module,
                        "mm_agents.errors": errors}.items():
        monkeypatch.setitem(sys.modules, name, value)
    return errors


def sse(content="COMPLETE", *, finish="stop", done=True):
    lines = ["data: " + json.dumps({"choices": [{"delta": {"content": content}}]})]
    if finish is not None:
        lines.append("data: " + json.dumps({"choices": [{"delta": {}, "finish_reason": finish}]}))
    if done:
        lines.append("data: [DONE]")
    return [line.encode() + b"\n" for line in lines]


def request_with_responses(monkeypatch, responses, **options):
    sent = []
    attempts = []
    remaining = iter(responses)

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def __iter__(self):
            value = next(remaining)
            if isinstance(value, Exception):
                raise value
            return iter(value)

    def urlopen(request, timeout):
        sent.append(json.loads(request.data))
        return Response()

    monkeypatch.setattr(transport.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(transport.time, "sleep", lambda _: None)
    payload = {"model": "custom-model", "messages": [{"role": "user", "content": "task"}],
               "max_tokens": 16384}
    before = copy.deepcopy(payload)
    try:
        result = transport.call_chat_completions(
            payload, base_url="https://example.invalid/v1", api_key="test-only",
            provider_name="Compatible model", reasoning_effort=None,
            retries=3, stream=True, attempt_log=attempts, **options,
        )
    except transport.OpenAICompatibleAPIError as exc:
        result = exc
    assert payload == before
    assert all(request == sent[0] for request in sent)
    return result, sent, attempts


@pytest.mark.parametrize("broken", [
    sse("PARTIAL", finish=None, done=False),
    sse("PARTIAL", done=False),
    sse("PARTIAL", finish=None),
    sse("PARTIAL", done=False) + [b'data: {"error":{"message":"upstream failed"}}\n', b'data: [DONE]\n'],
    sse("PARTIAL", done=False) + [b'data: {broken-json\n', b'data: [DONE]\n'],
    sse("PARTIAL", done=False) + [b'data: {"error":"failed","choices":[{"delta":{"content":"BAD"},"finish_reason":"stop"}]}\n', b'data: [DONE]\n'],
    sse("PARTIAL", done=False) + [b'data: {"choices":"corrupt"}\n', b'data: [DONE]\n'],
    http.client.IncompleteRead(b"partial", 100),
])
def test_broken_stream_is_discarded_before_success(monkeypatch, broken):
    result, sent, attempts = request_with_responses(monkeypatch, [broken, sse()])
    assert result == "COMPLETE"
    assert len(sent) == 2
    assert attempts[0]["status"] in {"stream_incomplete", "upstream_error", "exception"}
    assert attempts[1]["status"] == "ok"


def test_three_truncated_streams_exhaust_budget(monkeypatch):
    result, sent, attempts = request_with_responses(
        monkeypatch, [sse("PARTIAL", done=False)] * 3
    )
    assert isinstance(result, transport.OpenAICompatibleAPIError)
    assert len(sent) == 3
    assert [a["status"] for a in attempts] == ["stream_incomplete"] * 3


def test_disabling_retries_does_not_allow_partial_actions(monkeypatch):
    result, sent, _ = request_with_responses(
        monkeypatch, [sse("PARTIAL", done=False)], retry_stream_errors=False
    )
    assert isinstance(result, transport.OpenAICompatibleAPIError)
    assert len(sent) == 1


def test_complete_stream_without_optional_usage_is_accepted(monkeypatch):
    result, sent, attempts = request_with_responses(
        monkeypatch, [[b": keepalive\n", b"event: message\n"] + sse()]
    )
    assert result == "COMPLETE"
    assert len(sent) == 1
    assert attempts[0]["status"] == "ok"


def test_valid_multiline_sse_event_is_accepted(monkeypatch):
    lines = [b'data: {"choices":\n',
             b'data: [{"delta":{"content":"COMPLETE"},"finish_reason":"stop"}]}\n',
             b'\n', b'data: [DONE]\n']
    result, sent, _ = request_with_responses(monkeypatch, [lines])
    assert result == "COMPLETE"
    assert len(sent) == 1


@pytest.mark.parametrize("profile_name", [n for n in AGENT_PROFILES if n != "gt-done"])
def test_all_model_profiles_use_shared_factory_and_16384(fake_agent_module, profile_name):
    profile = get_agent_profile(profile_name)
    assert profile.agent_config.agent_factory == SHARED_AGENT_FACTORY
    env = {**profile.env, "OPENAI_API_KEY": "test-only", "OPENAI_BASE_URL": "https://gateway.test/v1",
           "ARENA_OPENAI_COMPAT_HOTSWAP_ENABLED": "false"}
    if profile_name == "openai-compatible":
        env["ARENA_MODEL_NAME"] = "unlisted-custom-model"
    with patch.dict(os.environ, env, clear=True), patch.object(
        transport, "_post_stream_json", return_value=(200, transport._decode_sse_response(sse()))
    ) as post:
        agent = transport.create_agent(replace(profile.agent_config, eval_mode="cli"))
        assert agent.settings["max_tokens"] == 16384
        payload = {"model": agent.settings["model"], "max_tokens": agent.settings["max_tokens"],
                   "messages": [{"role": "user", "content": "observation"}]}
        assert agent.call_llm(payload) == "COMPLETE"
    request = post.call_args.kwargs["payload"]
    assert request[env.get("ARENA_MODEL_TOKEN_LIMIT_FIELD", "max_tokens")] == 16384
    assert request["model"] == env["ARENA_MODEL_NAME"]
    assert post.call_args.args[0] == "https://gateway.test/v1/chat/completions"
    if profile_name in MODEL_PRESETS:
        assert request["reasoning_effort"] == MODEL_PRESETS[profile_name][1]


def test_generic_factory_defaults_and_failure_propagation(fake_agent_module):
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-only"}, clear=True), patch.object(
        transport, "_post_stream_json", return_value=(200, transport._decode_sse_response(sse(done=False)))
    ) as post, patch.object(transport.time, "sleep"):
        agent = transport.create_agent(AgentConfig(name="arbitrary-model", eval_mode="gui"))
        assert agent.settings["max_tokens"] == 16384
        with pytest.raises(fake_agent_module.ModelAPIError) as error:
            agent.predict("task", {})
        assert error.value.attempts == 3
        assert len(agent._llm_attempts) == post.call_count == 3
        assert all(a["status"] != "ok" for a in agent._llm_attempts)


def test_token_parameter_names_are_allowed_but_credentials_are_not():
    assert _parse_agent_env([
        "ARENA_MODEL_MAX_TOKENS=16384", "ARENA_MODEL_TOKEN_LIMIT_FIELD=max_completion_tokens"
    ]) == {"ARENA_MODEL_MAX_TOKENS": "16384", "ARENA_MODEL_TOKEN_LIMIT_FIELD": "max_completion_tokens"}
    for key in ["OPENAI_API_KEY", "ARENA_MODEL_AUTH_TOKEN", "PASSWORD"]:
        with pytest.raises(ValueError, match="sensitive"):
            _parse_agent_env([f"{key}=test-only"])


def test_payload_field_conversion_is_configurable_and_non_mutating():
    for field in ["max_tokens", "max_completion_tokens"]:
        original = {"max_tokens": 16384, "messages": []}
        prepared = transport.prepare_payload(original, reasoning_effort=None,
                                             reasoning_field="none", max_tokens_field=field)
        assert prepared[field] == 16384
        assert len(set(prepared) & {"max_tokens", "max_completion_tokens"}) == 1
        assert original == {"max_tokens": 16384, "messages": []}
    with pytest.raises(ValueError, match="Unsupported token limit field"):
        transport.prepare_payload({}, reasoning_effort=None, reasoning_field="none", max_tokens_field="typo")


def test_unresolved_auto_mode_is_rejected_before_model_creation():
    with pytest.raises(ValueError, match="must be resolved"):
        transport.create_agent(AgentConfig(name="custom", eval_mode="auto"))
