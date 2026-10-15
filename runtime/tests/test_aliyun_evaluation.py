import importlib
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from engiworld.cloud_eval import check_cloud_config, resolve_image
from engiworld.scheduler.runner import ensure_engine_importable


def test_image_selection_by_region_and_snapshot(tmp_path):
    catalog = tmp_path / 'images.json'
    catalog.write_text(json.dumps({'regions': {'cn-beijing': {
        'AutoCAD2024': {'image_id': 'm-autocad'}}}}))
    assert resolve_image('AutoCAD2024', None, catalog, 'cn-beijing') == 'm-autocad'
    assert resolve_image('Other', 'm-custom', catalog, 'cn-shanghai') == 'm-custom'
    with pytest.raises(ValueError, match='No image'):
        resolve_image('AutoCAD2024', None, catalog, 'cn-shanghai')


@pytest.fixture
def cloud(monkeypatch):
    for name in ('ACCESS_KEY_ID', 'ACCESS_KEY_SECRET', 'REGION', 'VSWITCH_ID',
                 'SECURITY_GROUP_ID', 'INSTANCE_TYPE', 'IMAGE_ID'):
        monkeypatch.setenv('ALIYUN_' + name, 'test-value')
    monkeypatch.setenv('ALIYUN_USE_PRIVATE_IP', '1')
    ensure_engine_importable(Path(__file__).resolve().parents[1] / 'engine')
    return importlib.import_module('desktop_env.providers.aliyun.manager')


def test_public_network_requires_bandwidth(cloud, monkeypatch):
    check_cloud_config()
    monkeypatch.setenv('ALIYUN_USE_PRIVATE_IP', '0')
    monkeypatch.setenv('ALIYUN_PUBLIC_BANDWIDTH', '0')
    with pytest.raises(ValueError, match='BANDWIDTH'):
        check_cloud_config()


def test_provision_inherits_large_image_and_password(cloud, monkeypatch):
    created = []
    image = NS(status='Available', size=500, disk_device_mappings=NS(disk_device_mapping=[
        NS(type='system', size='500'), NS(type='data', size='30', snapshot_id='s-data')]))
    client = NS(
        describe_images=lambda req: NS(body=NS(images=NS(image=[image]))),
        run_instances=lambda req: (created.append(req) or NS(
            body=NS(instance_id_sets=NS(instance_id_set=['i-created'])))))
    monkeypatch.setattr(cloud, 'ECSClient', lambda config: client)
    monkeypatch.setattr(cloud, '_wait_for_instance_running', lambda *args: None)
    monkeypatch.setattr(cloud, 'ENABLE_TTL', True)
    monkeypatch.setenv('ALIYUN_PUBLIC_BANDWIDTH', '0')
    assert cloud._allocate_vm() == 'i-created'
    assert len(created) == 1
    request = created[0]
    assert request.system_disk.size == '500'
    assert request.data_disk[0].snapshot_id == 's-data'
    assert request.data_disk[0].size == 30
    assert request.data_disk[0].delete_with_instance is True
    assert request.password_inherit is True
    assert request.internet_max_bandwidth_out == 0
    assert request.auto_release_time and request.client_token


def test_creation_error_does_not_repeat_paid_request(cloud, monkeypatch):
    attempts = []
    def create(req):
        attempts.append(req)
        raise RuntimeError('insufficient quota')
    client = NS(describe_images=lambda req: NS(body=NS(images=NS(image=[
        NS(status='Available', size=50, disk_device_mappings=None)]))), run_instances=create)
    monkeypatch.setattr(cloud, 'ECSClient', lambda config: client)
    with pytest.raises(RuntimeError, match='quota'):
        cloud._allocate_vm()
    assert len(attempts) == 1


def test_private_ip_is_usable_without_public_ip(cloud, monkeypatch):
    module = importlib.import_module('desktop_env.providers.aliyun.provider')
    provider = module.AliyunProvider()
    instance = NS(vpc_attributes=NS(private_ip_address=NS(ip_address=['10.1.2.3'])),
                  public_ip_address=NS(ip_address=[]), eip_address=None)
    monkeypatch.setattr(provider, '_describe_instance', lambda _: NS(body=NS(instances=NS(instance=[instance]))))
    monkeypatch.setattr(module, '_wait_until_server_ready', lambda _: None)
    assert provider.get_ip_address('i-test') == '10.1.2.3'

@pytest.mark.parametrize('failure', ['reset', 'budget'])
def test_cloud_cli_releases_instance_after_task_failure(cloud, monkeypatch, tmp_path, failure):
    import sys
    from engiworld import cloud_eval
    from engiworld.active_time import ActiveTimeBudgetExceeded
    provider_module = importlib.import_module('desktop_env.providers.aliyun.provider')
    closed = []
    monkeypatch.setattr(cloud_eval, 'preflight', lambda *args: NS(
        task_id='sample/task-01', metadata={'snapshot': 'AutoCAD2024', 'os_type': 'Windows'}))
    monkeypatch.setattr(cloud_eval, '_agent_config_for_instance', lambda config, *args: config)
    monkeypatch.setattr(cloud_eval, '_agent_config_for_task', lambda config, *args: config)
    monkeypatch.setattr(cloud_eval, 'load_task_config', lambda *args: {})
    monkeypatch.setattr(cloud, '_allocate_vm', lambda: 'i-owned')
    monkeypatch.setattr(provider_module, 'AliyunProvider', lambda: NS(
        region='cn-beijing', client=NS(describe_instances=lambda req: NS(
            body=NS(instances=NS(instance=[NS(instance_id='i-owned')])))),
        stop_emulator=lambda instance: closed.append(instance)))
    class Environment:
        def __init__(self, **kwargs):
            assert kwargs['path_to_vm'] == 'i-owned'
        def reset(self, **kwargs):
            if failure == 'budget':
                raise ActiveTimeBudgetExceeded('deadline')
            raise RuntimeError('reset failed')
        def close(self):
            closed.append('environment')
    monkeypatch.setitem(sys.modules, 'desktop_env.desktop_env', NS(DesktopEnv=Environment))
    assert cloud_eval.main(['--task', 'sample/task-01', '--image-id', 'm-test',
                            '--smoke-test', '--result-dir', str(tmp_path)]) == 1
    result = json.loads(next(tmp_path.glob('*/summary.json')).read_text())
    assert result['instance_released'] is True
    assert result['error_category'] == ('environment_timeout' if failure == 'budget' else 'environment_error')
    assert closed == ['environment', 'i-owned']


def test_shared_image_name_resolves_without_fixed_id(tmp_path, monkeypatch):
    from engiworld import cloud_eval
    catalog = tmp_path / 'images.json'
    catalog.write_text(json.dumps({'regions': {'cn-beijing': {
        'FreeCAD': {'image_name': 'EngiWorld-FreeCAD-release'}}}}))
    calls = []
    monkeypatch.setattr(cloud_eval, 'find_cloud_image', lambda name, region: (
        calls.append((name, region)) or 'm-shared'))
    assert cloud_eval.resolve_image('FreeCAD', None, catalog, 'cn-beijing') == 'm-shared'
    assert calls == [('EngiWorld-FreeCAD-release', 'cn-beijing')]
