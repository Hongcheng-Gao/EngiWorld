import os
import time
import logging
import json
import volcenginesdkcore
import volcenginesdkautoscaling
import volcenginesdkecs.models as ecs_models
from volcenginesdkcore.rest import ApiException
from volcenginesdkecs.api import ECSApi

from desktop_env.providers.base import Provider
from desktop_env.providers.volcengine.manager import _allocate_vm

logger = logging.getLogger("desktopenv.providers.volcengine.VolcengineProvider")
logger.setLevel(logging.INFO)

WAIT_DELAY = 15
MAX_ATTEMPTS = 10


def _terminate_on_close() -> bool:
    return os.getenv("VOLCENGINE_TERMINATE_ON_CLOSE", "false").lower() in {"1", "true", "yes"}


def _first_instance_or_raise(response, instance_id: str, region: str):
    instances = getattr(response, "instances", None) or []
    if not instances:
        raise RuntimeError(
            f"Volcengine DescribeInstances returned no instance for instance_id={instance_id!r} "
            f"in region={region!r}. The instance may have been terminated, the worker may be "
            "using the wrong VOLCENGINE_REGION, or the credentials may point to a different "
            "account/project."
        )
    return instances[0]


def _private_ip_from_env(instance_id: str) -> str | None:
    raw_mapping = os.getenv("VOLCENGINE_INSTANCE_PRIVATE_IPS", "").strip()
    if raw_mapping:
        try:
            mapping = json.loads(raw_mapping)
        except json.JSONDecodeError as exc:
            raise ValueError("VOLCENGINE_INSTANCE_PRIVATE_IPS must be a JSON object.") from exc
        if not isinstance(mapping, dict):
            raise ValueError("VOLCENGINE_INSTANCE_PRIVATE_IPS must be a JSON object.")
        private_ip = mapping.get(instance_id)
        if private_ip:
            return str(private_ip)

    single_instance_id = os.getenv("VOLCENGINE_INSTANCE_ID", "").strip()
    single_private_ip = os.getenv("VOLCENGINE_INSTANCE_PRIVATE_IP", "").strip()
    if single_private_ip and (not single_instance_id or single_instance_id == instance_id):
        return single_private_ip
    return None


class VolcengineProvider(Provider):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.region = os.getenv("VOLCENGINE_REGION", "eu-central-1")
        self.client = self._create_client()

    def _create_client(self) -> ECSApi:
        configuration = volcenginesdkcore.Configuration()
        configuration.ak = os.getenv('VOLCENGINE_ACCESS_KEY_ID')
        configuration.sk = os.getenv('VOLCENGINE_SECRET_ACCESS_KEY')
        configuration.region = os.getenv('VOLCENGINE_REGION')
        configuration.client_side_validation = True
        # set default configuration
        volcenginesdkcore.Configuration.set_default(configuration)
        return ECSApi()

    def start_emulator(self, path_to_vm: str, headless: bool, *args, **kwargs):
        logger.info("Starting Volcengine VM...")

        try:
            private_ip = _private_ip_from_env(path_to_vm)
            if private_ip:
                logger.info(
                    "Using master-provided private IP %s for Volcengine instance %s; "
                    "skipping worker-side ECS DescribeInstances.",
                    private_ip,
                    path_to_vm,
                )
                return

            # Check the instance status.
            instance_info = self.client.describe_instances(ecs_models.DescribeInstancesRequest(
                instance_ids=[path_to_vm]
            ))
            instance = _first_instance_or_raise(instance_info, path_to_vm, self.region)
            status = instance.status
            logger.info(f"Instance {path_to_vm} current status: {status}")

            if status == 'RUNNING':
                logger.info(f"Instance {path_to_vm} is already running. Skipping start.")
                return

            if status == 'STOPPED':
                # Start the instance.
                self.client.start_instance(ecs_models.StartInstancesRequest(instance_ids=[path_to_vm]))
                logger.info(f"Instance {path_to_vm} is starting...")

                # Wait for the instance to start running.
                for attempt in range(MAX_ATTEMPTS):
                    time.sleep(WAIT_DELAY)
                    instance_info = self.client.describe_instances(ecs_models.DescribeInstancesRequest(
                        instance_ids=[path_to_vm]
                    ))
                    instance = _first_instance_or_raise(instance_info, path_to_vm, self.region)
                    status = instance.status

                    if status == 'RUNNING':
                        logger.info(f"Instance {path_to_vm} is now running.")
                        break
                    elif status == 'ERROR':
                        raise Exception(f"Instance {path_to_vm} failed to start")
                    elif attempt == MAX_ATTEMPTS - 1:
                        raise Exception(f"Instance {path_to_vm} failed to start within timeout")
            else:
                logger.warning(f"Instance {path_to_vm} is in status '{status}' and cannot be started.")

        except ApiException as e:
            logger.error(f"Failed to start the Volcengine VM {path_to_vm}: {str(e)}")
            raise

    def get_ip_address(self, path_to_vm: str) -> str:
        logger.info("Getting Volcengine VM IP address...")

        try:
            private_ip = _private_ip_from_env(path_to_vm)
            if private_ip:
                logger.info(
                    "Using master-provided private IP %s for Volcengine instance %s.",
                    private_ip,
                    path_to_vm,
                )
                return private_ip

            instance_info = self.client.describe_instances(ecs_models.DescribeInstancesRequest(
                instance_ids=[path_to_vm]
            ))

            instance = _first_instance_or_raise(instance_info, path_to_vm, self.region)
            eip_address = getattr(instance, "eip_address", None)
            public_ip = getattr(eip_address, "ip_address", None)
            network_interfaces = getattr(instance, "network_interfaces", None) or []
            if not network_interfaces:
                raise RuntimeError(f"Instance {path_to_vm} has no network interface.")
            private_ip = network_interfaces[0].primary_ip_address
            if not private_ip:
                raise RuntimeError(f"Instance {path_to_vm} has no private IP address.")

            if public_ip:
                vnc_url = f"http://{public_ip}:5910/vnc.html"
                logger.info("=" * 80)
                logger.info(f"🖥️  VNC Web Access URL: {vnc_url}")
                logger.info(f"📡 Public IP: {public_ip}")
                logger.info(f"🏠 Private IP: {private_ip}")
                logger.info("=" * 80)
                print(f"\n🌐 VNC Web Access URL: {vnc_url}")
                print(f"📍 Please open the above address in the browser for remote desktop access\n")
            else:
                logger.info(
                    "No public IP address available for VNC access; "
                    "using private IP %s for OSWorld server access.",
                    private_ip,
                )

            return private_ip

        except ApiException as e:
            logger.error(f"Failed to retrieve IP address for the instance {path_to_vm}: {str(e)}")
            raise

    def save_state(self, path_to_vm: str, snapshot_name: str):
        logger.info("Saving Volcengine VM state...")

        try:
            # Create an image.
            response = self.client.create_image(ecs_models.CreateImageRequest(
                snapshot_id=snapshot_name,
                instance_id=path_to_vm,
                description=f"OSWorld snapshot: {snapshot_name}"
            ))
            image_id = response['image_id']
            logger.info(f"Image {image_id} created successfully from instance {path_to_vm}.")
            return image_id
        except ApiException as e:
            logger.error(f"Failed to create image from the instance {path_to_vm}: {str(e)}")
            raise

    def revert_to_snapshot(self, path_to_vm: str, snapshot_name: str):
        logger.info(f"Reverting Volcengine VM to snapshot: {snapshot_name}...")

        try:
            # Delete the original instance.
            self.client.delete_instance(ecs_models.DeleteInstanceRequest(
                instance_id=path_to_vm,
            ))
            logger.info(f"Old instance {path_to_vm} has been deleted.")

            # Create the instance.
            new_instance_id = _allocate_vm()

            logger.info(f"New instance {new_instance_id} launched from image {snapshot_name}.")
            logger.info(f"Waiting for instance {new_instance_id} to be running...")

            # Wait for the new instance to start running.
            while True:
                instance_info = self.client.describe_instances(ecs_models.DescribeInstancesRequest(
                    instance_ids=[new_instance_id]
                ))
                instance = _first_instance_or_raise(instance_info, new_instance_id, self.region)
                status = instance.status
                if status == 'RUNNING':
                    break
                elif status in ['STOPPED', 'ERROR']:
                    raise Exception(f"New instance {new_instance_id} failed to start, status: {status}")
                time.sleep(5)

            logger.info(f"Instance {new_instance_id} is ready.")

            # Get the new instance IP address.
            try:
                instance_info = self.client.describe_instances(ecs_models.DescribeInstancesRequest(
                    instance_ids=[new_instance_id]
                ))
                instance = _first_instance_or_raise(instance_info, new_instance_id, self.region)
                public_ip = instance.eip_address.ip_address
                if public_ip:
                    vnc_url = f"http://{public_ip}:5910/vnc.html"
                    logger.info("=" * 80)
                    logger.info(f"🖥️  New Instance VNC Web Access URL: {vnc_url}")
                    logger.info(f"📡 Public IP: {public_ip}")
                    logger.info(f"🆔 New Instance ID: {new_instance_id}")
                    logger.info("=" * 80)
                    print(f"\n🌐 New Instance VNC Web Access URL: {vnc_url}")
                    print(f"📍 Please open the above address in the browser for remote desktop access\n")
            except Exception as e:
                logger.warning(f"Failed to get VNC address for new instance {new_instance_id}: {e}")

            return new_instance_id

        except ApiException as e:
            logger.error(f"Failed to revert to snapshot {snapshot_name} for the instance {path_to_vm}: {str(e)}")
            raise

    def stop_emulator(self, path_to_vm, region=None):
        logger.info(f"Stopping Volcengine VM {path_to_vm}...")

        if not _terminate_on_close():
            logger.info(
                "Skipping Volcengine instance termination because "
                "VOLCENGINE_TERMINATE_ON_CLOSE is not enabled."
            )
            return

        try:
            self.client.delete_instance(ecs_models.DeleteInstanceRequest(
                instance_id=path_to_vm,
            ))
            logger.info(f"Instance {path_to_vm} has been terminated.")
        except ApiException as e:
            logger.error(f"Failed to stop the Volcengine VM {path_to_vm}: {str(e)}")
            raise
