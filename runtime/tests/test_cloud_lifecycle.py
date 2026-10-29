"""Failure-injection tests: all paid cloud and model requests are replaced."""
import json
import sys
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from engiworld import cloud_eval
from engiworld.active_time import ActiveTimeBudgetExceeded
from engiworld.cloud_journal import CloudJournal, cleanup_journals
from engiworld.cloud_models import resolve_model
from engiworld.scheduler import cloud_factory, runner
from engiworld.scheduler.aliyun_ecs import AliyunEcsClient, AliyunLaunchConfig
from engiworld.scheduler.schemas import EvalConfig, InstanceRecord, TaskResult, TaskSpec
from engiworld.scheduler.volcengine_ecs import InstanceLaunchGroup


@pytest.fixture
def cloud_env(monkeypatch):
    for suffix in ('ACCESS_KEY_ID', 'ACCESS_KEY_SECRET', 'REGION', 'VSWITCH_ID',
                   'SECURITY_GROUP_ID', 'INSTANCE_TYPE', 'IMAGE_ID'):
        monkeypatch.setenv('ALIYUN_' + suffix, 'offline-test')
    monkeypatch.setenv('ALIYUN_PUBLIC_BANDWIDTH', '0')
    monkeypatch.setenv('OPENAI_API_KEY', 'offline-secret')


class FakeEcsApi:
    def __init__(self):
        self.instances = {}
        self.creates = []
        self.deletes = []
        self.fail_delete = False
        self.lose_response = False
        self.hide_by_name = False
        self.boot = 'Running'

    def describe_images(self, request):
        mappings = NS(disk_device_mapping=[NS(type='system', size='500'),
            NS(type='data', size='30', snapshot_id='s-data')])
        return NS(body=NS(images=NS(image=[NS(status='Available', size=500,
            os_type='windows', disk_device_mappings=mappings)])))

    def run_instances(self, request):
        self.creates.append(request)
        self.instances['i-created'] = NS(instance_id='i-created', instance_name=request.instance_name,
            image_id=request.image_id, os_type='windows', status=self.boot,
            vpc_attributes=NS(private_ip_address=NS(ip_address=['10.0.0.1'])))
        if self.lose_response:
            raise TimeoutError('accepted create response lost')
        return NS(body=NS(instance_id_sets=NS(instance_id_set=['i-created'])))

    def describe_instances(self, request):
        if request.instance_name and self.hide_by_name:
            items = []
        else:
            items = list(self.instances.values())
        # Model an asynchronous deletion: it remains visible for one poll.
        for item in items:
            if item.status == 'Deleting':
                del self.instances[item.instance_id]
        return NS(body=NS(instances=NS(instance=items), total_count=len(items)))

    def delete_instances(self, request):
        self.deletes.append(request.instance_id)
        if self.fail_delete:
            raise RuntimeError('permission denied')
        self.instances['i-created'].status = 'Deleting'


def backend(tmp_path, api):
    return AliyunEcsClient(AliyunLaunchConfig('offline-test', 'offline-type'),
                           client=api, journal_dir=tmp_path)


def launch(ecs, timeout=1):
    image = ecs.get_image('m-test', 'AutoCAD2024')
    return ecs.run_instance_groups([InstanceLaunchGroup(image, 1, 'AutoCAD2024', 'Windows')],
                                   run_id='offline', wait_timeout_seconds=timeout)


def test_large_image_data_disks_and_durable_creation_intent(tmp_path, cloud_env):
    api = FakeEcsApi()
    ecs = backend(tmp_path, api)
    records = launch(ecs)
    request = api.creates[0]
    assert request.system_disk.size == '500'
    assert request.data_disk[0].snapshot_id == 's-data'
    assert request.data_disk[0].delete_with_instance is True
    assert request.auto_release_time and request.client_token
    data = json.loads(next(tmp_path.rglob('*.json')).read_text())
    assert data['client_token'] == request.client_token
    assert data['instance_ids'] == ['i-created']
    assert 'offline-secret' not in json.dumps(data)
    assert records[0].metadata['provider'] == 'aliyun'


def test_boot_failure_preserves_id_and_failed_cleanup(tmp_path, cloud_env):
    api = FakeEcsApi()
    api.boot = 'Pending'
    api.fail_delete = True
    with pytest.raises(TimeoutError):
        launch(backend(tmp_path, api), timeout=0)
    data = json.loads(next(tmp_path.rglob('*.json')).read_text())
    assert data['instance_ids'] == ['i-created']
    assert data['cleanup_error'] == 'permission denied'
    assert data['state'] == 'created'


@pytest.mark.parametrize('hidden', [False, True])
def test_lost_create_response_is_reconciled_or_recorded_unknown(tmp_path, cloud_env, hidden):
    api = FakeEcsApi()
    api.lose_response, api.hide_by_name = True, hidden
    with pytest.raises(TimeoutError):
        launch(backend(tmp_path, api))
    data = json.loads(next(tmp_path.rglob('*.json')).read_text())
    assert len(api.creates) == 1
    assert data['client_token'] and data['instance_name']
    assert data['state'] == ('submitting' if hidden else 'released')
    assert bool(api.instances) is hidden
    assert bool(data.get('cleanup_error')) is hidden


def test_delete_once_then_confirm_absence(tmp_path, cloud_env):
    api = FakeEcsApi()
    ecs = backend(tmp_path, api)
    launch(ecs)
    ecs.terminate_instances(['i-created'])
    ecs.terminate_instances(['i-created'])
    assert api.deletes == [['i-created']]


def test_rollback_never_deletes_another_transaction(tmp_path, cloud_env):
    foreign = CloudJournal(tmp_path / 'previous', 'aliyun', region='offline-test', instance_name='other')
    foreign.update(state='created', instance_ids=['i-other'])
    api = FakeEcsApi()
    api.lose_response = True
    with pytest.raises(TimeoutError):
        launch(backend(tmp_path, api))
    assert json.loads(foreign.path.read_text())['state'] == 'created'
    assert api.deletes == [['i-created']]


def test_cleanup_rejects_other_cloud_and_region(tmp_path, cloud_env):
    journal = CloudJournal(tmp_path, 'volcengine', region='other', instance_name='other')
    journal.update(state='created', instance_ids=['i-other'])
    api = FakeEcsApi()
    assert cleanup_journals(backend(tmp_path, api), tmp_path)
    assert not api.deletes


TASK = TaskSpec('single-software-execution/cli/autocad/task-01',
               'single-software-execution/cli/autocad', 'task-01', metadata={
                   'snapshot': 'AutoCAD2024', 'os_type': 'Windows', 'eval_mode': 'cli',
                   'base_task_id': 'single-software-execution/cli/autocad/task-01',
                   'source_task_id': 'offline-windows', 'task_path': 'offline/task-01.json',
                   'task_kind': 'single-software-execution',
                   'task_json': {'id': 'offline-windows', 'instruction': 'Draw', 'config': []}})


@contextmanager
def no_timer(seconds):
    yield NS(metrics=lambda: {'active_duration_seconds': 1.0})


@pytest.fixture
def single(monkeypatch, tmp_path, cloud_env):
    api = FakeEcsApi()
    ecs = backend(tmp_path / 'unused', api)
    def factory(provider, journal_dir):
        ecs.journal_dir = journal_dir
        return ecs
    monkeypatch.setattr(cloud_factory, 'make_cloud_client', factory)
    monkeypatch.setattr(cloud_eval, 'preflight', lambda *args: TASK)
    monkeypatch.setattr(cloud_eval, 'task_deadline', no_timer)
    monkeypatch.setattr(cloud_eval, 'run_single_task', lambda *args, **kwargs: TaskResult(
        TASK.task_id, TASK.domain, TASK.example_id, 1.0, str(tmp_path)))
    def run(*extra):
        code = cloud_eval.main(['--task', TASK.task_id, '--image-id', 'm-test',
            '--agent', 'kimi-k3-max', '--result-dir', str(tmp_path / 'results'), *extra])
        summaries = sorted((tmp_path / 'results').glob('*/summary.json'), key=lambda p: p.stat().st_mtime_ns)
        return code, json.loads(summaries[-1].read_text())
    return run, api


def test_cleanup_error_cannot_replace_native_score(single):
    run, api = single
    api.fail_delete = True
    code, summary = run()
    assert code == 1
    assert summary['score'] == 1.0
    assert summary['status'] == 'completed'
    assert summary['cleanup_error']


@pytest.mark.parametrize('retain', [True, False])
def test_api_interruption_has_no_score_and_retention_is_explicit(single, monkeypatch, retain):
    run, api = single
    monkeypatch.setattr(cloud_eval, 'run_single_task', lambda *args, **kwargs: TaskResult(
        TASK.task_id, TASK.domain, TASK.example_id, 0.0, '', error='API stopped', error_category='model_api'))
    code, summary = run(*([] if retain else ['--no-retain-api-incomplete-instances']))
    assert code == 1 and summary['score'] is None and summary['status'] == 'api_incomplete'
    assert bool(api.instances) is retain
    assert summary['model_config']['reasoning_effort'] == 'max'
    assert summary['model_config']['token_limit_field'] == 'max_completion_tokens'


def test_real_runner_does_not_delete_a_cloud_owned_instance(tmp_path, monkeypatch):
    runner.ensure_engine_importable(Path(__file__).resolve().parents[1] / 'engine')
    closed = []
    class Environment:
        def __init__(self, **kwargs):
            assert kwargs['manage_lifecycle'] is False
        def close(self):
            closed.append(True)
            raise ActiveTimeBudgetExceeded('cleanup timeout must be unreachable')
    def execute(*args):
        args[-1].append(1.0)
    monkeypatch.setitem(sys.modules, 'desktop_env.desktop_env', NS(DesktopEnv=Environment))
    monkeypatch.setitem(sys.modules, 'lib_run_single', NS(run_single_example_terminal=execute))
    config = EvalConfig('offline', result_dir=str(tmp_path), task_root=str(tmp_path))
    agent = resolve_model('kimi-k3-max')[0].agent_config
    result = runner.run_single_task(TASK, InstanceRecord('i-test', '', os_type='Windows'), config,
        agent, agent_factory=lambda cfg: object(), provider_name='aliyun', manage_lifecycle=False)
    assert result.score == 1.0 and not closed


def test_custom_models_require_full_protocol():
    with pytest.raises(ValueError):
        resolve_model('openai-compatible', model='custom')
    _, env = resolve_model('openai-compatible', model='custom', reasoning_effort='none', max_tokens=32768)
    assert env['ARENA_MODEL_MAX_TOKENS'] == '32768'


@pytest.mark.skipif(sys.platform != 'linux', reason='requires real SIGALRM')
def test_completed_score_survives_slow_post_result_cleanup(tmp_path, monkeypatch):
    import time

    from engiworld.active_time import ActiveTaskDeadline
    runner.ensure_engine_importable(Path(__file__).resolve().parents[1] / 'engine')
    monkeypatch.setitem(sys.modules, 'desktop_env.desktop_env', NS(DesktopEnv=lambda **kw: object()))
    monkeypatch.setitem(sys.modules, 'lib_run_single', NS(
        run_single_example_terminal=lambda *args: args[-1].append(1.0)))
    monkeypatch.setattr(runner.shutil, 'rmtree', lambda *a, **kw: time.sleep(0.4))
    config = EvalConfig('offline', result_dir=str(tmp_path), task_root=str(tmp_path))
    budget = ActiveTaskDeadline(0.2)
    with budget.running():
        result = runner.run_single_task(TASK, InstanceRecord('i-test', '', os_type='Windows'),
            config, resolve_model('kimi-k3-max')[0].agent_config,
            agent_factory=lambda cfg: object(), provider_name='aliyun', manage_lifecycle=False)
    assert result.score == 1.0
    assert budget.metrics()['active_duration_seconds'] < 0.2


def test_both_clouds_share_distributed_plan(monkeypatch):
    from engiworld.scheduler.master import _agent_settings_from_args, build_parser
    for provider in ('aliyun', 'volcengine'):
        args = build_parser().parse_args(['plan', '--cloud-provider', provider,
            '--agent', 'kimi-k3-max', '--max-tokens', '32768', '--reasoning-effort', 'max'])
        _, cfg, env = _agent_settings_from_args(args)
        assert env['ARENA_MODEL_MAX_TOKENS'] == '32768'
        assert cfg.cli_multi_max_steps == 150


@pytest.mark.parametrize('category,status', [('model_api', 'api_incomplete'), ('infra', 'infra_incomplete')])
def test_existing_redis_completion_does_not_score_interruptions(category, status):
    import fakeredis

    from engiworld.scheduler.redis_store import RedisStore
    store = RedisStore('', 'offline', client=fakeredis.FakeRedis(decode_responses=True))
    task = replace(TASK, metadata={**TASK.metadata, 'attempt': 1})
    store.client.hset(store.key('task:' + task.task_id), mapping={
        'worker_id': 'w', 'instance_id': 'i-test', 'attempt': '1', 'max_attempts': '1', 'score': '1.0'})
    store.client.hset(store.key('instance:i-test'), mapping={'worker_id': 'w', 'status': 'leased'})
    store.complete_task_and_release_instance(task, InstanceRecord('i-test', ''), 'w',
        score=0.0, error='offline failure', error_category=category)
    record = store.client.hgetall(store.key('task:' + task.task_id))
    assert record['status'] == status and 'score' not in record


@pytest.mark.parametrize('provider', ['aliyun', 'volcengine'])
def test_master_start_persists_provider_and_uses_existing_queue(tmp_path, monkeypatch, cloud_env, provider):
    import fakeredis

    from engiworld.scheduler import master
    from engiworld.scheduler.redis_store import RedisStore
    store = RedisStore('', 'batch', client=fakeredis.FakeRedis(decode_responses=True))
    ecs = backend(tmp_path / 'instances', FakeEcsApi())
    monkeypatch.setattr(ecs, 'list_images', lambda: [ecs.get_image('m-test', 'AutoCAD2024')])
    monkeypatch.setattr(master, 'RedisStore', lambda *a, **kw: store)
    monkeypatch.setattr(master, 'client_for_store', lambda store: ecs)
    monkeypatch.setattr(master, '_load_tasks_from_args', lambda *a, **kw: [TASK])
    monkeypatch.setattr(master, '_vm_osworld_settings_from_args', lambda args: (None, None))
    args = master.build_parser().parse_args(['start', '--cloud-provider', provider,
        '--agent', 'kimi-k3-max', '--num-vms', '1', '--global-max-vms', '0'])
    args.resolved_agent_profile, args.resolved_agent_config, args.resolved_agent_env = master._agent_settings_from_args(args)
    master._start(EvalConfig('batch', result_dir=str(tmp_path)), args)
    assert store.client.hget(store.key('meta'), 'cloud_provider') == provider
    claimed = store.claim_task('worker', lease_ttl_seconds=60)
    assert claimed.task_id == TASK.task_id
    instance = store.claim_instance('worker', TASK.task_id, lease_ttl_seconds=60)
    assert instance.instance_id == 'i-created'


@pytest.mark.parametrize('provider', ['aliyun', 'volcengine'])
def test_worker_uses_persisted_provider_and_scheduler_owns_lifecycle(tmp_path, monkeypatch, provider):
    from engiworld.scheduler import worker
    seen = []
    monkeypatch.setattr(worker, '_refresh_leases_until_done', lambda *a: None)
    monkeypatch.setattr(worker, 'upload_task_artifacts', lambda *a, **kw: None)
    def execute(*args, **kwargs):
        seen.append(kwargs)
        return TaskResult(TASK.task_id, TASK.domain, TASK.example_id, None,
                          str(tmp_path), error='API stopped', error_category='model_api')
    monkeypatch.setattr(worker, 'run_single_task', execute)
    completion = []
    def complete(**kwargs):
        completion.append(kwargs)
        return {'task_status': 'api_incomplete'}
    store = NS(record_worker_heartbeat=lambda *a, **kw: None,
               complete_task_and_release_instance=complete)
    task = replace(TASK, metadata={**TASK.metadata, 'attempt': 1})
    worker._run_claimed_task(store, 'worker', task,
        InstanceRecord('i-test', '', metadata={'provider': provider}),
        EvalConfig('batch'), resolve_model('kimi-k3-max')[0].agent_config, {}, 'kimi-k3-max',
        NS(reuse_instances=False))
    assert seen == [{'provider_name': provider, 'manage_lifecycle': False}]
    assert completion[0]['error_category'] == 'model_api'


def test_volcengine_sdk_create_has_durable_idempotency_before_request(tmp_path, monkeypatch):
    from engiworld.scheduler.volcengine_ecs import (
        EcsImage,
        VolcengineEcsClient,
        VolcengineLaunchConfig,
    )
    config = VolcengineLaunchConfig('region', 'offline-ak', 'offline-sk',
        'subnet', 'security-group', 'instance-type', 'zone', allocate_public_ip=False)
    observed = []
    def create(request):
        journal = json.loads(next(tmp_path.glob('*.json')).read_text())
        assert journal['state'] == 'submitting'
        assert journal['client_token'] == request.client_token
        assert journal['instance_name'] == request.instance_name
        observed.append(request)
        return NS(instance_ids=['i-volcengine'])
    monkeypatch.setattr(VolcengineEcsClient, '_create_api', lambda self: NS(run_instances=create))
    ecs = VolcengineEcsClient(config)
    ecs.journal_dir = tmp_path
    ids = ecs._run_instances_once(EcsImage('image-test', 'AutoCAD2024', 'Windows',
        'available', 'private', None, 500), 1, 'batch', 'AutoCAD2024', 500)
    assert ids == ['i-volcengine'] and len(observed) == 1
    assert json.loads(next(tmp_path.glob('*.json')).read_text())['instance_ids'] == ids


def test_lost_delete_response_is_success_only_after_confirmed_absence(tmp_path, cloud_env):
    api = FakeEcsApi()
    ecs = backend(tmp_path, api)
    launch(ecs)
    original = api.delete_instances
    def lose_delete(request):
        original(request)
        raise TimeoutError('delete response lost')
    api.delete_instances = lose_delete
    ecs.terminate_instances(['i-created'])
    assert len(api.deletes) == 1 and not api.instances
