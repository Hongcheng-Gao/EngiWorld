import logging
import os
import time

import dotenv
import requests
from alibabacloud_ecs20140526 import models as ecs_models
from alibabacloud_ecs20140526.client import Client as ECSClient
from alibabacloud_tea_util.client import Client as UtilClient

from desktop_env.providers.base import VMManager

dotenv.load_dotenv()

# Allocation validates configuration; connecting to an existing VM needs no image ID.


logger = logging.getLogger("desktopenv.providers.aliyun.AliyunVMManager")
logger.setLevel(logging.INFO)

ALIYUN_INSTANCE_TYPE = os.getenv("ALIYUN_INSTANCE_TYPE")
ALIYUN_ACCESS_KEY_ID = os.getenv("ALIYUN_ACCESS_KEY_ID")
ALIYUN_ACCESS_KEY_SECRET = os.getenv("ALIYUN_ACCESS_KEY_SECRET")
ALIYUN_REGION = os.getenv("ALIYUN_REGION")
ALIYUN_IMAGE_ID = os.getenv("ALIYUN_IMAGE_ID")
ALIYUN_SECURITY_GROUP_ID = os.getenv("ALIYUN_SECURITY_GROUP_ID")
ALIYUN_VSWITCH_ID = os.getenv("ALIYUN_VSWITCH_ID")
ALIYUN_RESOURCE_GROUP_ID = os.getenv("ALIYUN_RESOURCE_GROUP_ID")

WAIT_DELAY = 20
MAX_ATTEMPTS = 15


def _allocate_vm(screen_size=(1920, 1080)):
    """Allocate through the journaled cloud backend, including legacy callers."""
    if screen_size != (1920, 1080):
        raise ValueError("Only 1920x1080 screen size is supported")
    from engiworld.scheduler.aliyun_ecs import AliyunEcsClient, AliyunLaunchConfig
    from engiworld.scheduler.volcengine_ecs import InstanceLaunchGroup
    config = AliyunLaunchConfig.from_env()
    client = AliyunEcsClient(config)
    image_id = os.environ["ALIYUN_IMAGE_ID"]
    image = client.get_image(image_id, image_id)
    return client.run_instance_groups([InstanceLaunchGroup(image, 1, image_id, image.os_type)],
                                     run_id="legacy-aliyun")[0].instance_id


def _wait_for_instance_running(
    client: ECSClient, instance_id: str, max_attempts: int = MAX_ATTEMPTS
):
    """Wait for instance to reach Running state"""
    for _ in range(max_attempts):
        try:
            req = ecs_models.DescribeInstancesRequest(
                region_id=ALIYUN_REGION,
                instance_ids=UtilClient.to_jsonstring([instance_id]),
            )
            response = client.describe_instances(req)

            if response.body.instances.instance:
                instance = response.body.instances.instance[0]
                status = instance.status
                logger.info(f"Instance {instance_id} status: {status}")

                if status == "Running":
                    return
                elif status in ["Stopped", "Stopping"]:
                    start_req = ecs_models.StartInstanceRequest(instance_id=instance_id)
                    client.start_instance(start_req)
                    logger.info(f"Started instance {instance_id}")

            time.sleep(WAIT_DELAY)

        except Exception as e:
            logger.warning(f"Error checking instance status: {e}")
            time.sleep(WAIT_DELAY)

    raise TimeoutError(
        f"Instance {instance_id} did not reach Running state within {max_attempts * WAIT_DELAY} seconds"
    )


def _wait_until_server_ready(public_ip: str):
    """Wait until the server is ready"""
    for _ in range(MAX_ATTEMPTS):
        try:
            logger.info(f"Checking server status on {public_ip}...")
            response = requests.get(f"http://{public_ip}:5000/", timeout=2)
            if response.status_code in (200, 404):
                logger.info(f"Server {public_ip} is ready")
                return
        except requests.RequestException:
            pass
        time.sleep(WAIT_DELAY)

    raise TimeoutError(
        f"Server {public_ip} did not respond within {MAX_ATTEMPTS * WAIT_DELAY} seconds"
    )


class AliyunVMManager(VMManager):
    """
    Aliyun ECS VM Manager for managing virtual machines on Aliyun Cloud.

    Aliyun ECS does not need to maintain a registry of VMs, as it can dynamically allocate and deallocate VMs.
    """

    def __init__(self, **kwargs):
        self.initialize_registry()

    def initialize_registry(self, **kwargs):
        pass

    def add_vm(self, vm_path, lock_needed=True, **kwargs):
        pass

    def _add_vm(self, vm_path):
        pass

    def delete_vm(self, vm_path, lock_needed=True, **kwargs):
        pass

    def _delete_vm(self, vm_path):
        pass

    def occupy_vm(self, vm_path, pid, lock_needed=True, **kwargs):
        pass

    def _occupy_vm(self, vm_path, pid):
        pass

    def check_and_clean(self, lock_needed=True, **kwargs):
        pass

    def _check_and_clean(self):
        pass

    def list_free_vms(self, lock_needed=True, **kwargs):
        pass

    def _list_free_vms(self):
        pass

    def get_vm_path(self, screen_size=(1920, 1080), **kwargs):
        """Get a VM path (instance ID) for use"""
        logger.info(
            f"Allocating new ECS instance in region {ALIYUN_REGION} with screen size {screen_size}"
        )

        try:
            instance_id = _allocate_vm(screen_size)
            logger.info(f"Successfully allocated instance {instance_id}")
            return instance_id

        except Exception as e:
            logger.error(f"Failed to allocate instance: {str(e)}")
            raise
