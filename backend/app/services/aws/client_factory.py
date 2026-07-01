from __future__ import annotations

import boto3
from botocore.config import Config

AWS_CLIENT_CONFIG = Config(retries={"max_attempts": 4, "mode": "standard"})


def _client(service_name: str, *, region: str, access_key_id: str, secret_access_key: str):
    return boto3.client(
        service_name,
        region_name=region,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        config=AWS_CLIENT_CONFIG,
    )


def get_ce_client(*, region: str, access_key_id: str, secret_access_key: str):
    return _client("ce", region=region, access_key_id=access_key_id, secret_access_key=secret_access_key)


def get_cloudwatch_client(*, region: str, access_key_id: str, secret_access_key: str):
    return _client("cloudwatch", region=region, access_key_id=access_key_id, secret_access_key=secret_access_key)


def get_ec2_client(*, region: str, access_key_id: str, secret_access_key: str):
    return _client("ec2", region=region, access_key_id=access_key_id, secret_access_key=secret_access_key)


def get_rds_client(*, region: str, access_key_id: str, secret_access_key: str):
    return _client("rds", region=region, access_key_id=access_key_id, secret_access_key=secret_access_key)


def get_elbv2_client(*, region: str, access_key_id: str, secret_access_key: str):
    return _client("elbv2", region=region, access_key_id=access_key_id, secret_access_key=secret_access_key)
