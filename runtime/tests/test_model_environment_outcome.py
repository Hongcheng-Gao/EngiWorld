from engiworld.scheduler.error_policy import (
    MODEL_ENVIRONMENT_ERROR_CATEGORY,
    classify_task_error,
)


def test_port_5000_connection_loss_remains_infrastructure():
    error = (
        "SandboxUnavailableError: [run_bash_script] still failing after 90s. "
        "HTTPConnectionPool(host='10.0.2.4', port=5000): Max retries exceeded; "
        "Failed to establish a new connection: [Errno 111] Connection refused"
    )
    assert classify_task_error(error, "infra") == "infra"


def test_screenshot_http_500_remains_infrastructure():
    error = (
        "SandboxUnavailableError: [get_screenshot] still failing after 90s. "
        "RuntimeError: HTTP 500: Internal Server Error"
    )
    assert classify_task_error(error, "infra") == "infra"


def test_legacy_model_environment_category_becomes_infrastructure():
    assert classify_task_error("OSWorld Server disconnected", MODEL_ENVIRONMENT_ERROR_CATEGORY) == "infra"


def test_unrelated_infrastructure_failure_remains_infrastructure():
    assert classify_task_error("cloud instance provisioning timed out", "infra") == "infra"


def test_model_api_failure_keeps_its_category():
    assert classify_task_error("HTTP 413", "model_api") == "model_api"
