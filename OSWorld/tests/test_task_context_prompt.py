from mm_agents.prompts import build_task_context_prompt


def test_open_task_prompt_mentions_software_choice_and_distractor():
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
    assert "Open-software task guidance" in prompt
    assert "distractor software: openscad" in prompt
    assert "Do not assume every listed application is equally suitable" in prompt


def test_multi_task_prompt_mentions_handoff_chain():
    prompt = build_task_context_prompt(
        {
            "id": "multi-cli-2-archicad-openstudio-task-01-windows",
            "related_apps": ["archicad", "openstudio"],
        },
        eval_mode="cli",
    )
    assert "Multi-software handoff task guidance" in prompt
    assert "Produce every required intermediate artifact" in prompt
    assert "each later stage consume the artifact from the previous stage" in prompt


def test_quantified_task_prompt_mentions_continuous_score():
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
    assert "Quantified-score task guidance" in prompt
    assert "continuous optimization task" in prompt
    assert "baseline_score=64.6854" in prompt
