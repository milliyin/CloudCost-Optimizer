from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from urllib.parse import urlparse

from botocore.exceptions import BotoCoreError, ClientError

from app.services.aws.client_factory import (
    get_apigateway_client,
    get_apigatewayv2_client,
    get_dynamodb_client,
    get_ec2_client,
    get_ecr_client,
    get_ecs_client,
    get_elbv2_client,
    get_lambda_client,
    get_rds_client,
    get_s3_client,
    get_sns_client,
    get_sqs_client,
)
from app.services.aws.common import translate_aws_error
from app.services.aws.credentials import AWSCredentials
from app.services.aws.retry import aws_retry


def _serialize_tags(tags: list[dict] | None) -> str:
    return json.dumps({tag["Key"]: tag["Value"] for tag in (tags or [])})


def _json_dumps(data: dict) -> str:
    return json.dumps(data, default=str)


def _client_kwargs(credentials: AWSCredentials) -> dict[str, str]:
    return {
        "region": credentials.region,
        "access_key_id": credentials.access_key_id,
        "secret_access_key": credentials.secret_access_key,
    }


def _queue_name(queue_url: str) -> str:
    return urlparse(queue_url).path.rsplit("/", maxsplit=1)[-1]


@aws_retry()
def _describe_instances(credentials: AWSCredentials) -> dict:
    return get_ec2_client(**_client_kwargs(credentials)).describe_instances()


@aws_retry()
def _describe_volumes(credentials: AWSCredentials) -> dict:
    return get_ec2_client(**_client_kwargs(credentials)).describe_volumes()


@aws_retry()
def _describe_addresses(credentials: AWSCredentials) -> dict:
    return get_ec2_client(**_client_kwargs(credentials)).describe_addresses()


@aws_retry()
def _describe_db_instances(credentials: AWSCredentials) -> dict:
    return get_rds_client(**_client_kwargs(credentials)).describe_db_instances()


@aws_retry()
def _describe_load_balancers(credentials: AWSCredentials) -> dict:
    return get_elbv2_client(**_client_kwargs(credentials)).describe_load_balancers()


@aws_retry()
def _list_lambda_functions(credentials: AWSCredentials) -> list[dict]:
    client = get_lambda_client(**_client_kwargs(credentials))
    functions: list[dict] = []
    marker: str | None = None

    while True:
        response = client.list_functions(**({"Marker": marker} if marker else {}))
        functions.extend(response.get("Functions", []))
        marker = response.get("NextMarker")
        if not marker:
            break

    return functions


@aws_retry()
def _list_buckets(credentials: AWSCredentials) -> list[dict]:
    client = get_s3_client(**_client_kwargs(credentials))
    buckets = client.list_buckets().get("Buckets", [])
    buckets_with_region: list[dict] = []

    for bucket in buckets:
        location = client.get_bucket_location(Bucket=bucket["Name"]).get("LocationConstraint")
        buckets_with_region.append(
            {
                **bucket,
                "ResolvedRegion": location or "us-east-1",
            }
        )

    return buckets_with_region


@aws_retry()
def _list_dynamodb_tables(credentials: AWSCredentials) -> list[dict]:
    client = get_dynamodb_client(**_client_kwargs(credentials))
    table_names: list[str] = []
    last_evaluated_table_name: str | None = None

    while True:
        response = client.list_tables(**({"ExclusiveStartTableName": last_evaluated_table_name} if last_evaluated_table_name else {}))
        table_names.extend(response.get("TableNames", []))
        last_evaluated_table_name = response.get("LastEvaluatedTableName")
        if not last_evaluated_table_name:
            break

    return [client.describe_table(TableName=name)["Table"] for name in table_names]


@aws_retry()
def _list_sqs_queues(credentials: AWSCredentials) -> list[dict]:
    client = get_sqs_client(**_client_kwargs(credentials))
    queue_urls: list[str] = []
    next_token: str | None = None

    while True:
        response = client.list_queues(**({"NextToken": next_token} if next_token else {}))
        queue_urls.extend(response.get("QueueUrls", []))
        next_token = response.get("NextToken")
        if not next_token:
            break

    queues: list[dict] = []
    for queue_url in queue_urls:
        attributes = client.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=["All"],
        ).get("Attributes", {})
        queues.append({"QueueUrl": queue_url, "Attributes": attributes})
    return queues


@aws_retry()
def _list_sns_topics(credentials: AWSCredentials) -> list[dict]:
    client = get_sns_client(**_client_kwargs(credentials))
    topics: list[dict] = []
    next_token: str | None = None

    while True:
        response = client.list_topics(**({"NextToken": next_token} if next_token else {}))
        topics.extend(response.get("Topics", []))
        next_token = response.get("NextToken")
        if not next_token:
            break

    return topics


@aws_retry()
def _list_ecs_clusters_and_services(credentials: AWSCredentials) -> tuple[list[dict], list[dict]]:
    client = get_ecs_client(**_client_kwargs(credentials))
    cluster_arns: list[str] = []
    next_token: str | None = None

    while True:
        response = client.list_clusters(**({"nextToken": next_token} if next_token else {}))
        cluster_arns.extend(response.get("clusterArns", []))
        next_token = response.get("nextToken")
        if not next_token:
            break

    clusters: list[dict] = []
    services: list[dict] = []
    if cluster_arns:
        described_clusters = client.describe_clusters(clusters=cluster_arns).get("clusters", [])
        clusters.extend(described_clusters)
        for cluster in described_clusters:
            service_arns: list[str] = []
            service_next_token: str | None = None
            while True:
                service_response = client.list_services(
                    cluster=cluster["clusterArn"],
                    **({"nextToken": service_next_token} if service_next_token else {}),
                )
                service_arns.extend(service_response.get("serviceArns", []))
                service_next_token = service_response.get("nextToken")
                if not service_next_token:
                    break
            if service_arns:
                services.extend(
                    client.describe_services(cluster=cluster["clusterArn"], services=service_arns).get("services", [])
                )

    return clusters, services


@aws_retry()
def _describe_ecr_repositories(credentials: AWSCredentials) -> list[dict]:
    client = get_ecr_client(**_client_kwargs(credentials))
    repositories: list[dict] = []
    next_token: str | None = None

    while True:
        response = client.describe_repositories(**({"nextToken": next_token} if next_token else {}))
        repositories.extend(response.get("repositories", []))
        next_token = response.get("nextToken")
        if not next_token:
            break

    return repositories


@aws_retry()
def _get_rest_apis(credentials: AWSCredentials) -> list[dict]:
    client = get_apigateway_client(**_client_kwargs(credentials))
    apis: list[dict] = []
    position: str | None = None

    while True:
        response = client.get_rest_apis(**({"position": position} if position else {}))
        apis.extend(response.get("items", []))
        position = response.get("position")
        if not position:
            break

    return apis


@aws_retry()
def _get_http_apis(credentials: AWSCredentials) -> list[dict]:
    client = get_apigatewayv2_client(**_client_kwargs(credentials))
    apis: list[dict] = []
    next_token: str | None = None

    while True:
        response = client.get_apis(**({"NextToken": next_token} if next_token else {}))
        apis.extend(response.get("Items", []))
        next_token = response.get("NextToken")
        if not next_token:
            break

    return apis


def _collect_ec2_instances(credentials: AWSCredentials, now: datetime) -> list[dict]:
    instances = _describe_instances(credentials)
    resources: list[dict] = []
    for reservation in instances.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            resources.append(
                {
                    "resource_id": instance["InstanceId"],
                    "resource_type": "ec2_instance",
                    "region": credentials.region,
                    "state": instance.get("State", {}).get("Name", ""),
                    "instance_type": instance.get("InstanceType", ""),
                    "tags_json": _serialize_tags(instance.get("Tags")),
                    "last_seen": now,
                }
            )
    return resources


def _collect_ebs_volumes(credentials: AWSCredentials, now: datetime) -> list[dict]:
    volumes = _describe_volumes(credentials)
    resources: list[dict] = []
    for volume in volumes.get("Volumes", []):
        attachments = volume.get("Attachments", [])
        resources.append(
            {
                "resource_id": volume["VolumeId"],
                "resource_type": "ebs_volume",
                "region": volume.get("AvailabilityZone", "")[:-1] if volume.get("AvailabilityZone") else credentials.region,
                "state": volume.get("State", ""),
                "instance_type": "",
                "tags_json": _json_dumps(
                    {
                        **{tag["Key"]: tag["Value"] for tag in volume.get("Tags", [])},
                        "attachments": attachments,
                    }
                ),
                "last_seen": now,
            }
        )
    return resources


def _collect_elastic_ips(credentials: AWSCredentials, now: datetime) -> list[dict]:
    addresses = _describe_addresses(credentials)
    resources: list[dict] = []
    for address in addresses.get("Addresses", []):
        resources.append(
            {
                "resource_id": address.get("AllocationId") or address.get("PublicIp", ""),
                "resource_type": "elastic_ip",
                "region": credentials.region,
                "state": "associated" if address.get("AssociationId") else "unassociated",
                "instance_type": "",
                "tags_json": _json_dumps(
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
    return resources


def _collect_rds_instances(credentials: AWSCredentials, now: datetime) -> list[dict]:
    db_instances = _describe_db_instances(credentials)
    return [
        {
            "resource_id": db_instance["DBInstanceIdentifier"],
            "resource_type": "rds_instance",
            "region": credentials.region,
            "state": db_instance.get("DBInstanceStatus", ""),
            "instance_type": db_instance.get("DBInstanceClass", ""),
            "tags_json": _json_dumps(
                {
                    "engine": db_instance.get("Engine", ""),
                    "arn": db_instance.get("DBInstanceArn", ""),
                }
            ),
            "last_seen": now,
        }
        for db_instance in db_instances.get("DBInstances", [])
    ]


def _collect_load_balancers(credentials: AWSCredentials, now: datetime) -> list[dict]:
    load_balancers = _describe_load_balancers(credentials)
    return [
        {
            "resource_id": lb["LoadBalancerArn"],
            "resource_type": "load_balancer",
            "region": credentials.region,
            "state": lb.get("State", {}).get("Code", ""),
            "instance_type": lb.get("Type", ""),
            "tags_json": _json_dumps(
                {
                    "name": lb.get("LoadBalancerName", ""),
                    "dns_name": lb.get("DNSName", ""),
                }
            ),
            "last_seen": now,
        }
        for lb in load_balancers.get("LoadBalancers", [])
    ]


def _collect_lambda_functions(credentials: AWSCredentials, now: datetime) -> list[dict]:
    lambda_functions = _list_lambda_functions(credentials)
    return [
        {
            "resource_id": function["FunctionName"],
            "resource_type": "lambda_function",
            "region": credentials.region,
            "state": function.get("State", function.get("LastUpdateStatus", "active")),
            "instance_type": function.get("Runtime", function.get("PackageType", "")),
            "tags_json": _json_dumps(
                {
                    "arn": function.get("FunctionArn", ""),
                    "handler": function.get("Handler", ""),
                    "memory_size": function.get("MemorySize", ""),
                    "timeout": function.get("Timeout", ""),
                }
            ),
            "last_seen": now,
        }
        for function in lambda_functions
    ]


def _collect_s3_buckets(credentials: AWSCredentials, now: datetime) -> list[dict]:
    buckets = _list_buckets(credentials)
    return [
        {
            "resource_id": bucket["Name"],
            "resource_type": "s3_bucket",
            "region": bucket.get("ResolvedRegion", "us-east-1"),
            "state": "active",
            "instance_type": "",
            "tags_json": _json_dumps({"creation_date": bucket.get("CreationDate")}),
            "last_seen": now,
        }
        for bucket in buckets
    ]


def _collect_dynamodb_tables(credentials: AWSCredentials, now: datetime) -> list[dict]:
    tables = _list_dynamodb_tables(credentials)
    return [
        {
            "resource_id": table["TableName"],
            "resource_type": "dynamodb_table",
            "region": credentials.region,
            "state": table.get("TableStatus", ""),
            "instance_type": table.get("BillingModeSummary", {}).get("BillingMode", ""),
            "tags_json": _json_dumps(
                {
                    "arn": table.get("TableArn", ""),
                    "table_class": table.get("TableClassSummary", {}).get("TableClass", ""),
                }
            ),
            "last_seen": now,
        }
        for table in tables
    ]


def _collect_sqs_queues(credentials: AWSCredentials, now: datetime) -> list[dict]:
    queues = _list_sqs_queues(credentials)
    resources: list[dict] = []
    for queue in queues:
        queue_url = queue["QueueUrl"]
        attributes = queue["Attributes"]
        queue_name = _queue_name(queue_url)
        resources.append(
            {
                "resource_id": queue_name,
                "resource_type": "sqs_queue",
                "region": credentials.region,
                "state": "active",
                "instance_type": "fifo" if queue_name.endswith(".fifo") else "standard",
                "tags_json": _json_dumps(
                    {
                        "url": queue_url,
                        "arn": attributes.get("QueueArn", ""),
                        "message_retention_seconds": attributes.get("MessageRetentionPeriod", ""),
                    }
                ),
                "last_seen": now,
            }
        )
    return resources


def _collect_sns_topics(credentials: AWSCredentials, now: datetime) -> list[dict]:
    topics = _list_sns_topics(credentials)
    return [
        {
            "resource_id": topic["TopicArn"].rsplit(":", maxsplit=1)[-1],
            "resource_type": "sns_topic",
            "region": credentials.region,
            "state": "active",
            "instance_type": "",
            "tags_json": _json_dumps({"arn": topic["TopicArn"]}),
            "last_seen": now,
        }
        for topic in topics
    ]


def _collect_ecs(credentials: AWSCredentials, now: datetime) -> list[dict]:
    clusters, services = _list_ecs_clusters_and_services(credentials)
    resources: list[dict] = []
    for cluster in clusters:
        resources.append(
            {
                "resource_id": cluster["clusterName"],
                "resource_type": "ecs_cluster",
                "region": credentials.region,
                "state": cluster.get("status", ""),
                "instance_type": "",
                "tags_json": _json_dumps({"arn": cluster.get("clusterArn", "")}),
                "last_seen": now,
            }
        )
    for service in services:
        resources.append(
            {
                "resource_id": service["serviceName"],
                "resource_type": "ecs_service",
                "region": credentials.region,
                "state": service.get("status", ""),
                "instance_type": service.get("launchType", ""),
                "tags_json": _json_dumps(
                    {
                        "arn": service.get("serviceArn", ""),
                        "cluster_arn": service.get("clusterArn", ""),
                        "desired_count": service.get("desiredCount", 0),
                    }
                ),
                "last_seen": now,
            }
        )
    return resources


def _collect_ecr_repositories(credentials: AWSCredentials, now: datetime) -> list[dict]:
    repositories = _describe_ecr_repositories(credentials)
    return [
        {
            "resource_id": repository["repositoryName"],
            "resource_type": "ecr_repository",
            "region": credentials.region,
            "state": "active",
            "instance_type": repository.get("imageTagMutability", ""),
            "tags_json": _json_dumps(
                {
                    "arn": repository.get("repositoryArn", ""),
                    "uri": repository.get("repositoryUri", ""),
                }
            ),
            "last_seen": now,
        }
        for repository in repositories
    ]


def _collect_api_gateways(credentials: AWSCredentials, now: datetime) -> list[dict]:
    rest_apis = _get_rest_apis(credentials)
    http_apis = _get_http_apis(credentials)
    resources: list[dict] = []
    for api in rest_apis:
        resources.append(
            {
                "resource_id": api["name"],
                "resource_type": "rest_api",
                "region": credentials.region,
                "state": "active",
                "instance_type": "rest",
                "tags_json": _json_dumps({"id": api.get("id", ""), "endpoint_configuration": api.get("endpointConfiguration", {})}),
                "last_seen": now,
            }
        )
    for api in http_apis:
        resources.append(
            {
                "resource_id": api["Name"],
                "resource_type": "http_api",
                "region": credentials.region,
                "state": "active",
                "instance_type": api.get("ProtocolType", ""),
                "tags_json": _json_dumps({"id": api.get("ApiId", ""), "api_endpoint": api.get("ApiEndpoint", "")}),
                "last_seen": now,
            }
        )
    return resources


def get_resource_inventory(credentials: AWSCredentials) -> tuple[list[dict], list[str]]:
    now = datetime.now(UTC)
    resources: list[dict] = []
    warnings: list[str] = []

    collectors: list[tuple[str, Callable[[AWSCredentials, datetime], list[dict]]]] = [
        ("EC2 inventory", _collect_ec2_instances),
        ("EBS inventory", _collect_ebs_volumes),
        ("Elastic IP inventory", _collect_elastic_ips),
        ("RDS inventory", _collect_rds_instances),
        ("Load balancer inventory", _collect_load_balancers),
        ("Lambda inventory", _collect_lambda_functions),
        ("S3 inventory", _collect_s3_buckets),
        ("DynamoDB inventory", _collect_dynamodb_tables),
        ("SQS inventory", _collect_sqs_queues),
        ("SNS inventory", _collect_sns_topics),
        ("ECS inventory", _collect_ecs),
        ("ECR inventory", _collect_ecr_repositories),
        ("API Gateway inventory", _collect_api_gateways),
    ]

    for service_name, collector in collectors:
        try:
            resources.extend(collector(credentials, now))
        except (ClientError, BotoCoreError) as error:
            warnings.append(str(translate_aws_error(error, service=service_name)))

    return resources, warnings
