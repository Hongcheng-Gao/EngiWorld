from desktop_env.evaluators.metrics import quantified_score


def test_quantified_score_prefers_score_json_over_stdout_boolean():
    result = {
        "stdout": "True\n",
        "score_json": '{"valid": true, "score": 73.25}',
    }

    assert quantified_score(result) == 73.25


def test_quantified_score_reads_json_from_stdout_last_line():
    result = "some setup output\n{\"score\": 12.5, \"valid\": true}\n"

    assert quantified_score(result) == 12.5


def test_quantified_score_uses_metric_output_field():
    result = {"score_json": '{"quality": 0.8125, "score": 0.1}'}

    assert quantified_score(result, metric={"output_field": "quality"}) == 0.8125


def test_quantified_score_boolean_fallback():
    assert quantified_score("True\n") == 1.0
    assert quantified_score("False\n") == 0.0
