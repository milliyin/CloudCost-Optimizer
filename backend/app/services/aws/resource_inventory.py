from __future__ import annotations

import json
from datetime import UTC, datetime

from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.services.aws.client_factory import get_ec2_client, get_elbv2_client, get_rds_client
from app.services.aws.common import translate_aws_error
from app.services.aws.retry import aws_retry


def _serialize_tags(tags: list[dict] | None) -> str:
    return json.dumps({tag["Key"]: tag["Value"] for tag in (tags or [])})


@aws_retry()
def _describe_instances() -> dict:
    return get_ec2_client().describe_instances()


@aws_retry()
def _describe_volumes() -> dict:
    return get_ec2_client().describe_volumes()


@aws_retry()
def _describe_addresses() -> dict:
    return get_ec2_client().describe_addresses()


@aws_retry()
def _describe_db_instances() -> dict:
    return get_rds_client().describe_db_instances()


@aws_retry()
def _describe_load_balancers() -> dict:
    return get_elbv2_client().describe_load_balancers()


def get_resource_inventory() -> list[dict]:
    try:
        instances = _describe_instances()
        volumes = _describe_volumes()
        addresses = _describe_addresses()
        db_instances = _describe_db_instances()
        load_balancers = _describe_load_balancers()
    except (ClientError, BotoCoreError) as error:
        raise translate_aws_error(error, service="AWS inventory") from error

    now = datetime.now(UTC)
    resources: list[dict] = []

    for reservation in instances.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            resources.append(
                {
                    "resource_id": instance["InstanceId"],
                    "resource_type": "ec2_instance",
                    "region": settings.aws_region,
                    "state": instance.get("State", {}).get("Name", ""),
                    "instance_type": instance.get("InstanceType", ""),
                    "tags_json": _serialize_tags(instance.get("Tags")),
                    "last_seen": now,
                }
            )

    for volume in volumes.get("Volumes", []):
        attachments = volume.get("Attachments", [])
        resources.append(
            {
                "resource_id": volume["VolumeId"],
                "resource_type": "ebs_volume",
                "region": volume.get("AvailabilityZone", "")[:-1] if volume.get("AvailabilityZone") else settings.aws_region,
                "state": volume.get("State", ""),
                "instance_type": "",
                "tags_json": json.dumps(
                    {
                        **{tag["Key"]: tag["Value"] for tag in volume.get("Tags", [])},
                        "attachments": attachments,
                    }
                ),
                "last_seen": now,
            }
        )

    for address in addresses.get("Addresses", []):
        resources.append(
            {
                "resource_id": address.get("AllocationId") or address.get("PublicIp", ""),
                "resource_type": "elastic_ip",
                "region": settings.aws_region,
                "state": "associated" if address.get("AssociationId") else "unassociated",
                "instance_type": "",
                "tags_json": json.dumps(
                    {
                        **{tag["Key"]: tag["Value"] for tag in address.get("Tags", [])},
                        "association_id": address.get("AssociationId", ""),
                        "instance_id": address.get("InstanceId", ""),
                        "public_ip": address.get("PublicIp", ""),
                    }
                ),
                "last_seen": now,
            }
        )

    for db_instance in db_instances.get("DBInstances", []):
        resources.append(
            {
                "resource_id": db_instance["DBInstanceIdentifier"],
                "resource_type": "rds_instance",
                "region": settings.aws_region,
                "state": db_instance.get("DBInstanceStatus", ""),
                "instance_type": db_instance.get("DBInstanceClass", ""),
                "tags_json": json.dumps(
                    {
                        "engine": db_instance.get("Engine", ""),
                        "arn": db_instance.get("DBInstanceArn", ""),
                    }
                ),
                "last_seen": now,
            }
        )

    for lb in load_balancers.get("LoadBalancers", []):
        resources.append(
            {
                "resource_id": lb["LoadBalancerArn"],
                "resource_type": "load_balancer",
                "region": settings.aws_region,
                "state": lb.get("State", {}).get("Code", ""),
                "instance_type": lb.get("Type", ""),
                "tags_json": json.dumps(
                    {
                        "name": lb.get("LoadBalancerName", ""),
                        "dns_name": lb.get("DNSName", ""),
                    }
                ),
                "last_seen": now,
            }
        )

    return resources
