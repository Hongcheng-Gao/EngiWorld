"""Explicit model protocol shared by single-task and distributed cloud runs."""
from __future__ import annotations

from engiworld.agents.profiles import get_agent_profile, profile_names


def add_model_arguments(parser):
    parser.add_argument("--agent", choices=profile_names())
    parser.add_argument("--model")
    parser.add_argument("--reasoning-effort")
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--token-limit-field", choices=["max_tokens", "max_completion_tokens"])


def resolve_model(name, *, model=None, reasoning_effort=None, max_tokens=None,
                  token_limit_field=None, overrides=None):
    profile = get_agent_profile(name)
    env = dict(profile.env)
    env.update(overrides or {})
    supplied = {"ARENA_MODEL_NAME": model, "ARENA_MODEL_REASONING_EFFORT": reasoning_effort,
                "ARENA_MODEL_MAX_TOKENS": str(max_tokens) if max_tokens is not None else None,
                "ARENA_MODEL_TOKEN_LIMIT_FIELD": token_limit_field}
    env.update({key: value for key, value in supplied.items() if value is not None})
    if name == "openai-compatible":
        required = ("ARENA_MODEL_NAME", "ARENA_MODEL_REASONING_EFFORT")
        if any(not env.get(key) for key in required):
            raise ValueError("Custom models require an explicit model and reasoning effort (use none to disable)")
        if max_tokens is None and "ARENA_MODEL_MAX_TOKENS" not in (overrides or {}):
            raise ValueError("Custom models require an explicit --max-tokens")
    if int(env["ARENA_MODEL_MAX_TOKENS"]) <= 0:
        raise ValueError("--max-tokens must be positive")
    env.setdefault("ARENA_MODEL_REASONING_FIELD", "reasoning_effort")
    env.setdefault("ARENA_MODEL_TOKEN_LIMIT_FIELD", "max_tokens")
    env.setdefault("ARENA_MODEL_ENSURE_FINAL_USER_TURN", "false")
    return profile, env


def model_record(name, env):
    return {"profile": name, "model": env.get("ARENA_MODEL_NAME"),
            "reasoning_effort": env.get("ARENA_MODEL_REASONING_EFFORT"),
            "reasoning_field": env["ARENA_MODEL_REASONING_FIELD"],
            "max_tokens": int(env["ARENA_MODEL_MAX_TOKENS"]),
            "token_limit_field": env["ARENA_MODEL_TOKEN_LIMIT_FIELD"],
            "ensure_final_user_turn": env["ARENA_MODEL_ENSURE_FINAL_USER_TURN"]}
