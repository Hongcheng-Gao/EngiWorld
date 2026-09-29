"""A no-model agent used for ground-truth verifier checks."""

from __future__ import annotations

from typing import Any

from engiworld.scheduler.schemas import AgentConfig


class GTDoneAgent:
    """Immediately finish the episode after task setup has injected GT outputs."""

    def reset(self, *args: Any, **kwargs: Any) -> None:
        return None

    def predict(
        self,
        instruction: str,
        obs: dict[str, Any],
    ) -> tuple[str, list[tuple[str, str]]]:
        return "Ground-truth artifacts have been injected; run verifier now.\n```DONE```", [
            ("DONE", "")
        ]


def create_agent(agent_config: AgentConfig) -> GTDoneAgent:
    return GTDoneAgent()
