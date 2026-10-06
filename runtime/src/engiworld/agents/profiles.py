"""Model presets are configuration data; all use one compatible API factory."""

from __future__ import annotations

from dataclasses import dataclass, replace

from engiworld.agents.openai_compatible import DEFAULT_MAX_TOKENS
from engiworld.scheduler.schemas import AgentConfig

SHARED_AGENT_FACTORY = "engiworld.agents.openai_compatible:create_agent"

# profile: (wire model, reasoning effort, token-limit field, final-user requirement)
MODEL_PRESETS = {
    "gpt-5.6-sol-xhigh": ("gpt-5.6-sol", "xhigh", "max_tokens", False),
    "claude-opus-5-max": ("claude-opus-5", "max", "max_tokens", False),
    "kimi-k3-max": ("kimi-k3", "max", "max_completion_tokens", False),
    "gemini-3.7-flash-high": ("gemini-3.7-flash", "high", "max_tokens", True),
    "qwen3.8-max-xhigh": ("qwen3.8-max", "xhigh", "max_tokens", False),
    "qwen3.8-flash-xhigh": ("qwen3.8-flash", "xhigh", "max_tokens", False),
    "deepseek-v4.1-flash-max": ("deepseek-v4.1-flash", "max", "max_tokens", False),
}
ENGIWORLD_FORMAL_PROFILE_NAMES = frozenset({"openai-compatible", *MODEL_PRESETS})
ENGIWORLD_FORMAL_STEP_LIMITS = {
    "max_steps": 200,
    "gui_max_steps": 200,
    "cli_max_steps": 100,
    "gui_multi_max_steps": 300,
    "cli_multi_max_steps": 150,
    "open_ended_max_steps": 150,
}


@dataclass(frozen=True)
class AgentProfile:
    name: str
    agent_config: AgentConfig
    env: dict[str, str]


def _model_profile(
    name: str,
    model: str | None = None,
    effort: str | None = None,
    token_field: str = "max_tokens",
    final_user: bool = False,
) -> AgentProfile:
    env = {
        "ARENA_OPENAI_COMPAT_HOTSWAP_ENABLED": "true",
        "ARENA_OPENAI_COMPAT_RUNTIME_CONFIG_DIR": "model-api",
        "ARENA_OPENAI_COMPAT_HOTSWAP_WAIT_SECONDS": "86400",
        "ARENA_OPENAI_COMPAT_HOTSWAP_POLL_SECONDS": "5",
        "ARENA_MODEL_MAX_TOKENS": str(DEFAULT_MAX_TOKENS),
        "ARENA_MODEL_TIMEOUT_SECONDS": "600",
        "ARENA_MODEL_API_RETRIES": "3",
        "ARENA_MODEL_STREAM": "true",
    }
    # Custom-model options come from the worker environment or --agent-env.
    # Named presets pin their protocol settings without a separate adapter.
    if model is not None:
        env.update({
            "ARENA_MODEL_NAME": model,
            "ARENA_MODEL_REASONING_EFFORT": effort or "none",
            "ARENA_MODEL_TOKEN_LIMIT_FIELD": token_field,
            "ARENA_MODEL_ENSURE_FINAL_USER_TURN": str(final_user).lower(),
        })
    return AgentProfile(
        name=name,
        agent_config=AgentConfig(
            name=name,
            agent_factory=SHARED_AGENT_FACTORY,
            action_space="pyautogui",
            observation_type="screenshot",
            eval_mode="auto",
            **ENGIWORLD_FORMAL_STEP_LIMITS,
            history_turns=15,
            sleep_after_execution=2.0,
            screen_width=1920,
            screen_height=1080,
            headless=True,
        ),
        env=env,
    )


AGENT_PROFILES = {
    name: _model_profile(name, *settings) for name, settings in MODEL_PRESETS.items()
}
AGENT_PROFILES["openai-compatible"] = _model_profile("openai-compatible")

# Keep old CLI profile names usable through the same implementation.
AGENT_PROFILES["kimi-k3"] = _model_profile(
    "kimi-k3", "kimi-k3", "max", "max_completion_tokens"
)
for _name in ("qwen3-vl-flash", "chatgpt-5.5", "qwen3.7-plus"):
    _profile = _model_profile(_name, _name)
    AGENT_PROFILES[_name] = replace(
        _profile,
        agent_config=replace(
            _profile.agent_config,
            max_steps=15,
            gui_max_steps=None,
            cli_max_steps=None,
            gui_multi_max_steps=None,
            cli_multi_max_steps=None,
            open_ended_max_steps=None,
        ),
    )

AGENT_PROFILES["gt-done"] = AgentProfile(
    name="gt-done",
    agent_config=AgentConfig(
        name="gt-done",
        agent_factory="engiworld.agents.gt_done:create_agent",
        action_space="pyautogui",
        observation_type="screenshot",
        max_steps=1,
        sleep_after_execution=0.1,
        screen_width=1920,
        screen_height=1080,
        headless=True,
    ),
    env={},
)


def profile_names() -> list[str]:
    return sorted(AGENT_PROFILES)


def get_agent_profile(name: str) -> AgentProfile:
    try:
        return AGENT_PROFILES[name]
    except KeyError as exc:
        choices = ", ".join(profile_names())
        raise ValueError(f"Unknown agent profile {name!r}. Available profiles: {choices}") from exc
