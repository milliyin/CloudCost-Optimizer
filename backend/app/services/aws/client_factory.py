from __future__ import annotations

import boto3
from botocore.config import Config

from app.core.config import settings

AWS_CLIENT_CONFIG = Config(retries={"max_attempts": 4, "mode": "standard"})


def _client(service_name: str):
    return boto3.client(
        service_name,
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        config=AWS_CLIENT_CONFIG,
    )


def get_ce_client():
    return _client("ce")


def get_cloudwatch_client():
    return _client("cloudwatch")


def get_ec2_client():
    return _client("ec2")


def get_rds_client():
    return _client("rds")


def get_elbv2_client():
    return _client("elbv2")
