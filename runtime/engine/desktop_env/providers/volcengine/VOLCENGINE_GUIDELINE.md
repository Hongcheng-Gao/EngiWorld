# Volcengine ECS provider configuration

Configure a Volcengine account with sufficient balance for pay-as-you-go ECS
instances, an IAM access key with ECS permissions, a VPC, subnet, security group,
and custom environment image. Creating one instance manually first helps verify
these settings.

## Environment variables

Set these values in your `.env` file:

```bash
VOLCENGINE_ACCESS_KEY_ID=your_access_key_id
VOLCENGINE_SECRET_ACCESS_KEY=your_secret_access_key
VOLCENGINE_REGION=ap-southeast-1
VOLCENGINE_IMAGE_ID=image-xxxxxxxxx
VOLCENGINE_INSTANCE_TYPE=ecs.e-c1m2.large
VOLCENGINE_SUBNET_ID=subnet-xxxxxxxxx
VOLCENGINE_SECURITY_GROUP_ID=sg-xxxxxxxxx
VOLCENGINE_ZONE_ID=zone-xxxxxxxxx
VOLCENGINE_DEFAULT_PASSWORD=your_default_password
```

## Network configuration

Create the VPC and subnet in the target region. The worker must be able to reach
the guest services. Configure security-group access for the ports used by your
image and restrict source addresses to the worker network and trusted administrators.

| Service | TCP port |
|---|---|
| SSH | 22 |
| HTTP | 80 |
| Environment service | 5000 |
| noVNC | 5910 |
| VNC service | 8006 |
| VLC service | 8080 |
| Additional image service | 8081 |
| Chrome remote debugging | 9222 |

Allow outbound access required by model requests, task resources, and package
installation.

## Custom images

Use an EngiWorld environment image matching the task's `snapshot`. Decompress the
QCOW2 archive, upload the disk to TOS in the target ECS region, and select
**Import image** in the ECS console. After import completes, use the resulting
custom image ID in the provider configuration.
