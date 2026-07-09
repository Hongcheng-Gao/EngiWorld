from mm_agents.prompts import build_task_context_prompt


def test_task_context_prompt_does_not_reveal_open_roles():
    prompt = build_task_context_prompt(
        {
            "id": "c-altium-orcad-open-task-01-windows",
            "related_apps": ["altium-designer", "cadence-orcad", "openscad"],
            "open_software_roles": {
                "candidate_software": ["altium-designer", "cadence-orcad"],
                "distractor_software": "openscad",
            },
        },
        eval_mode="cli",
    )
    assert prompt == ""


def test_task_context_prompt_does_not_add_multi_guidance():
    prompt = build_task_context_prompt(
        {
            "id": "multi-cli-2-archicad-openstudio-task-01-windows",
            "related_apps": ["archicad", "openstudio"],
        },
        eval_mode="cli",
    )
    assert prompt == ""


def test_task_context_prompt_does_not_reveal_quantified_metric_metadata():
    prompt = build_task_context_prompt(
        {
            "id": "q-c-kicad-task-01-ubuntu",
            "evaluator": {"func": "quantified_score"},
            "quantified_metric": {
                "name": "weighted decoupling loop cost",
                "direction": "maximize",
                "baseline_score": 64.6854,
                "output_field": "score",
            },
        },
        eval_mode="cli",
    )
    assert prompt == ""
