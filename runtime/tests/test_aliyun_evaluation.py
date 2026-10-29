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




def test_private_ip_is_usable_without_public_ip(cloud, monkeypatch):
    module = importlib.import_module('desktop_env.providers.aliyun.provider')
    provider = module.AliyunProvider()
    instance = NS(vpc_attributes=NS(private_ip_address=NS(ip_address=['10.1.2.3'])),
                  public_ip_address=NS(ip_address=[]), eip_address=None)
    monkeypatch.setattr(provider, '_describe_instance', lambda _: NS(body=NS(instances=NS(instance=[instance]))))
    monkeypatch.setattr(module, '_wait_until_server_ready', lambda _: None)
    assert provider.get_ip_address('i-test') == '10.1.2.3'


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
