"""EngiWorld experiment-specific prompt settings.

The action-space prompts live in :mod:`mm_agents.prompts`.  This module only
describes what the selected experiment exposes to the model, so an ablation
can change without copying the shared action format.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ExperimentProfile:
    name: str
    observation: str
    resources: str
    image_action: str | None = None
    fixed_reference_image: bool = False
    fixed_reference_path: bool = False


PROFILES: dict[str, ExperimentProfile] = {
    "base": ExperimentProfile("base", "Use the observation supplied by the selected action-space mode.", "Use the files and applications named in the task."),
    "open_engineering": ExperimentProfile("open_engineering", "After you act, the next message contains terminal output and any images returned by readimg.", "Inspect the task inputs and environment, then choose, install, or configure the engineering tools needed for the task.", "readimg"),
    "gui_main": ExperimentProfile("gui_main", "Each turn provides one screenshot of the current desktop.", "The required applications and any inputs explicitly provided by the task are prepared in the runtime. Open and handle them through the visible GUI workflow."),
    "gui_message_initial": ExperimentProfile("gui_message_initial", "The reference image provided with the task is available together with each request. Each turn also provides the current desktop screenshot.", "The required applications and any other inputs explicitly provided by the task are prepared in the runtime. Open and handle them through the visible GUI workflow.", fixed_reference_image=True),
    "gui_screenshot_a11y": ExperimentProfile("gui_screenshot_a11y", "Each turn contains the current desktop screenshot and accessibility tree.", "The required applications and any inputs explicitly provided by the task are prepared in the runtime. Open and handle them through the visible GUI workflow."),
    "cli_main": ExperimentProfile("cli_main", "After you act, the next message contains the resulting terminal output and any images returned by readimg.", "readimg can inspect declared task drawings and visual files produced by the required application.", "readimg"),
    "cli_message_initial": ExperimentProfile("cli_message_initial", "The reference image provided with the task is available together with each request. After you act, the next message contains the resulting terminal output and any images returned by readimg.", "Use the reference image provided with the task together with the task inputs and the required applications' command-line, batch, headless, or official scripting interfaces. readimg can inspect visual files produced during the task.", "readimg", fixed_reference_image=True),
    "cli_message_no_readimg": ExperimentProfile("cli_message_no_readimg", "The reference image provided with the task is available together with each request. After you act, the next message contains the resulting terminal output.", "Use the reference image provided with the task together with the task inputs and the required applications' command-line, batch, headless, or official scripting interfaces.", fixed_reference_image=True),
    "cli_environment_initial": ExperimentProfile("cli_environment_initial", "After you act, the next message contains the resulting terminal output and any images returned by readimg.", "The initial task drawings are available at the paths provided by the task setup; readimg can inspect them and visual files produced during the task.", "readimg", fixed_reference_path=True),
    "cli_text": ExperimentProfile("cli_text", "After you act, the next message contains terminal output only.", "Use the task inputs and the required applications' textual CLI, batch, or scripting interfaces."),
}

ALIASES = {
    "gui": "gui_main",
    "gui-main": "gui_main",
    "gui-message": "gui_message_initial",
    "gui-screenshot-a11y": "gui_screenshot_a11y",
    "cli": "cli_main",
    "cli-main": "cli_main",
    "cli-text": "cli_text",
    "cli-message": "cli_message_initial",
    "cli-message-no-readimg": "cli_message_no_readimg",
    "cli-environment": "cli_environment_initial",
    "extreme": "open_engineering",
    "open-engineering": "open_engineering",
}


def normalize_experiment_profile(profile: str | None, eval_mode: str = "") -> str:
    raw = (profile or "").strip().lower()
    raw = ALIASES.get(raw, raw)
    if not raw:
        raw = {
            "gui": "gui_main",
            "computer13": "base",
            "gui-a11y": "base",
            "gui-screenshot-a11y": "gui_screenshot_a11y",
            "cli": "cli_main",
            "cli-text": "cli_text",
            "extreme": "open_engineering",
        }.get(eval_mode, "")
    if raw not in PROFILES:
        allowed = ", ".join(sorted(PROFILES))
        raise ValueError(f"Unknown experiment profile {profile!r}; expected one of: {allowed}")
    return raw


def experiment_profile_allows_readimg(profile: str) -> bool:
    return PROFILES[normalize_experiment_profile(profile)].image_action == "readimg"


def experiment_profile_image_action(profile: str) -> str | None:
    return PROFILES[normalize_experiment_profile(profile)].image_action


def experiment_profile_has_fixed_reference_image(profile: str) -> bool:
    return PROFILES[normalize_experiment_profile(profile)].fixed_reference_image


def experiment_profile_has_fixed_reference_path(profile: str) -> bool:
    return PROFILES[normalize_experiment_profile(profile)].fixed_reference_path


def render_experiment_prompt(
    profile: str,
    runtime: Mapping[str, Any] | None = None,
) -> str:
    """Validate the selected profile without exposing runner settings."""
    normalize_experiment_profile(profile)
    return ""


def build_task_context_prompt(task_config, eval_mode: str = "", experiment_profile: str | None = None) -> str:
    task_config = task_config or {}
    selected = experiment_profile or task_config.get("_engiworld_experiment_profile") or task_config.get("experiment_profile")
    if not selected and not eval_mode:
        return ""
    return render_experiment_prompt(normalize_experiment_profile(selected, eval_mode=eval_mode))
