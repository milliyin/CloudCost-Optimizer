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


def get_lambda_client(*, region: str, access_key_id: str, secret_access_key: str):
    return _client("lambda", region=region, access_key_id=access_key_id, secret_access_key=secret_access_key)


def get_s3_client(*, region: str, access_key_id: str, secret_access_key: str):
    return _client("s3", region=region, access_key_id=access_key_id, secret_access_key=secret_access_key)


def get_dynamodb_client(*, region: str, access_key_id: str, secret_access_key: str):
    return _client("dynamodb", region=region, access_key_id=access_key_id, secret_access_key=secret_access_key)


def get_sqs_client(*, region: str, access_key_id: str, secret_access_key: str):
    return _client("sqs", region=region, access_key_id=access_key_id, secret_access_key=secret_access_key)


def get_sns_client(*, region: str, access_key_id: str, secret_access_key: str):
    return _client("sns", region=region, access_key_id=access_key_id, secret_access_key=secret_access_key)


def get_ecs_client(*, region: str, access_key_id: str, secret_access_key: str):
    return _client("ecs", region=region, access_key_id=access_key_id, secret_access_key=secret_access_key)


def get_ecr_client(*, region: str, access_key_id: str, secret_access_key: str):
    return _client("ecr", region=region, access_key_id=access_key_id, secret_access_key=secret_access_key)


def get_apigateway_client(*, region: str, access_key_id: str, secret_access_key: str):
    return _client("apigateway", region=region, access_key_id=access_key_id, secret_access_key=secret_access_key)


def get_apigatewayv2_client(*, region: str, access_key_id: str, secret_access_key: str):
    return _client("apigatewayv2", region=region, access_key_id=access_key_id, secret_access_key=secret_access_key)
