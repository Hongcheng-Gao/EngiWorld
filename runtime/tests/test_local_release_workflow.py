import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

from engiworld import prepare_tasks
from engiworld.local_eval import LocalTaskTimeout, main, preflight
from engiworld.agents.profiles import get_agent_profile
from engiworld.scheduler.runner import run_single_task
from engiworld.scheduler.schemas import EvalConfig, InstanceRecord, TaskSpec
from engiworld.scheduler.task_loader import load_tasks

ROOT = Path(__file__).resolve().parents[2] / "task"


def test_docker_provider_waits_for_software_vm_without_kvm(tmp_path, monkeypatch):
    import docker
    from engiworld.scheduler.runner import ensure_engine_importable

    ensure_engine_importable(Path(__file__).resolve().parents[1] / "engine")
    from desktop_env.providers.docker import provider as docker_provider

    calls = []

    class Containers:
        def run(self, image, **kwargs):
            calls.append((image, kwargs))
            return SimpleNamespace(stop=lambda: None, remove=lambda: None)

    monkeypatch.setattr(docker, "from_env", lambda: SimpleNamespace(containers=Containers()))
    exists = docker_provider.os.path.exists
    monkeypatch.setattr(docker_provider.os.path, "exists",
                        lambda path: False if str(path) == "/dev/kvm" else exists(path))
    vm = docker_provider.DockerProvider("local")
    monkeypatch.setattr(vm, "_get_available_port", lambda port: port)
    monkeypatch.setattr(vm, "_wait_for_vm_ready", lambda timeout=300: calls.append(("ready", timeout)))

    image = tmp_path / "example.qcow2"
    image.touch()
    vm.start_emulator(str(image), headless=True, os_type="Ubuntu")

    assert calls[0][0] == "happysixd/osworld-docker"
    assert calls[0][1]["devices"] == []
    assert calls[0][1]["environment"]["KVM"] == "N"
    assert calls[1] == ("ready", 900)


def test_reverse_tasks_are_single_software_and_legacy_selection_still_works():
    tasks = load_tasks(ROOT)
    assert len(tasks) == 1301
    assert not any(task.task_id.startswith("reverse/") for task in tasks)
    aliases = json.loads((ROOT / "aliases.json").read_text())
    aliases = {old: new for old, new in aliases.items() if old.startswith("reverse/")}
    assert len(aliases) == 10
    assert len(load_tasks(ROOT, path_prefixes=["reverse/"])) == 10
    for old, new in aliases.items():
        selected = load_tasks(ROOT, path_prefixes=[old + "/"])
        assert [task.task_id for task in selected] == [new]
        assert selected[0].metadata["eval_mode"] == "gui"
        assert selected[0].metadata["task_kind"] == "single-software"


def test_manifest_covers_all_reference_image_tasks():
    _, assets = prepare_tasks.asset_entries(ROOT)
    image_tasks = load_tasks(ROOT, path_prefixes=["image-based-modeling/"])
    assert len(image_tasks) == 120
    for task in image_tasks:
        assert any(entry["path"].startswith(task.task_id + "/init_file/")
                   and Path(entry["path"]).suffix.lower() in {".png", ".jpg", ".jpeg"}
                   for entry in assets)


def test_prepare_restores_pinned_bytes_and_rejects_local_changes(tmp_path):
    data = b"reference image bytes"
    entry = {"path": "task-v/example/task-01/init_file/ref.png", "source": "task/original/ref.png",
             "size": len(data), "git_blob": prepare_tasks.blob_hash(data)}
    manifest = {"source_repository": "https://github.com/owner/repo", "revision": "pinned"}
    with patch.object(prepare_tasks.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=data)):
        assert prepare_tasks.restore_asset(tmp_path, manifest, entry) == "restored"
        assert prepare_tasks.restore_asset(tmp_path, manifest, entry) == "present"
    target = tmp_path / entry["path"]
    target.write_bytes(b"local edit")
    with pytest.raises(ValueError, match="refusing to overwrite"):
        prepare_tasks.restore_asset(tmp_path, manifest, entry)
    assert target.read_bytes() == b"local edit"


def test_prepare_rejects_corrupt_download(tmp_path):
    entry = {"path": "input.bin", "source": "task/input.bin", "size": 4, "git_blob": "0" * 40}
    with patch.object(prepare_tasks.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=b"bad!")):
        with pytest.raises(ValueError, match="checksum mismatch"):
            prepare_tasks.restore_asset(tmp_path, {}, entry)
    assert not (tmp_path / "input.bin").exists()


def test_private_source_can_use_existing_git_credentials(tmp_path):
    data = b"image bytes"
    entry = {"path": "ref.png", "source": "task/ref.png", "size": len(data),
             "git_blob": prepare_tasks.blob_hash(data)}
    manifest = {"source_repository": "https://github.com/owner/repo", "revision": "pinned"}
    with patch.object(prepare_tasks.subprocess, "run", return_value=SimpleNamespace(returncode=1)), \
         patch.object(prepare_tasks, "urlopen", side_effect=HTTPError("url", 404, "Not Found", {}, None)), \
         patch.object(prepare_tasks, "authenticated_git_asset", return_value=data) as fallback:
        assert prepare_tasks.restore_asset(tmp_path, manifest, entry) == "restored"
    fallback.assert_called_once_with(tmp_path, manifest, entry)
    assert (tmp_path / "ref.png").read_bytes() == data


def test_asset_path_cannot_escape_task_root(tmp_path):
    with pytest.raises(ValueError, match="outside"):
        prepare_tasks.asset_path(tmp_path, "../outside")


def test_check_rejects_unknown_task_without_loading_vm():
    with pytest.raises(SystemExit) as error:
        main(["--task", "missing/task-01", "--check"])
    assert error.value.code == 2


@pytest.mark.parametrize("outcome", ["success", "api_error", "infra", "deadline"])
def test_local_runner_uses_image_and_cleans_up_on_every_exit(tmp_path, outcome):
    events = []

    class Environment:
        def __init__(self, **kwargs):
            assert kwargs["provider_name"] == "docker"
            assert kwargs["path_to_vm"] == "/images/example.qcow2"
            events.append("start")

        def close(self):
            events.append("close")

    def run_example(agent, env, example, max_steps, instruction, args, result_dir, scores):
        assert max_steps == 200
        events.append("run")
        if outcome == "api_error":
            raise RuntimeError("API interrupted")
        if outcome == "infra":
            failure = RuntimeError("Evaluator or desktop preparation failed")
            failure.error_category = "infra"
            raise failure
        if outcome == "deadline":
            raise LocalTaskTimeout("deadline")
        scores.append(1.0)

    task = TaskSpec("task-v/example/task-01", "task-v/example", "task-01",
                    metadata={"task_json": {"id": "example", "instruction": "draw", "config": []}})
    config = EvalConfig(run_id="test", result_dir=str(tmp_path / "results"), task_root=str(tmp_path))
    modules = {"lib_run_single": SimpleNamespace(run_single_example=run_example),
               "desktop_env.desktop_env": SimpleNamespace(DesktopEnv=Environment)}
    with patch.dict("sys.modules", modules), patch("engiworld.scheduler.runner.ensure_engine_importable"):
        call = lambda: run_single_task(task, InstanceRecord("local", ""), config,
                                       get_agent_profile("openai-compatible").agent_config,
                                       agent_factory=lambda config: object(), provider_name="docker",
                                       path_to_vm="/images/example.qcow2")
        if outcome == "deadline":
            with pytest.raises(LocalTaskTimeout):
                call()
        else:
            result = call()
            assert result.ok == (outcome == "success")
            if outcome == "infra":
                assert result.score is None and result.error_category == "infra"
            else:
                assert result.score == (1.0 if outcome == "success" else 0.0)
    assert events == ["start", "run", "close"]


def test_preflight_detects_missing_upload_before_vm_start(tmp_path):
    folder = tmp_path / "task-v/example/task-01"
    folder.mkdir(parents=True)
    (folder / "task-01.json").write_text(json.dumps({
        "id": "example", "snapshot": "Example", "instruction": "draw",
        "config": [{"type": "upload_file", "parameters": {"files": [
            {"local_path": "task-01/input.bin", "path": "/tmp/input.bin"}]}}],
    }))
    (tmp_path / "assets-manifest.json").write_text('{"assets": []}')
    with pytest.raises(ValueError, match="Missing or modified"):
        preflight(tmp_path, "task-v/example/task-01")
