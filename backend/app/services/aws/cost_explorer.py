from __future__ import annotations

from datetime import date, timedelta

from botocore.exceptions import BotoCoreError, ClientError

from app.services.aws.client_factory import get_ce_client
from app.services.aws.common import translate_aws_error
from app.services.aws.retry import aws_retry


def _default_start_end(lookback_days: int) -> tuple[str, str]:
    end_date = date.today() + timedelta(days=1)
    start_date = end_date - timedelta(days=lookback_days)
    return start_date.isoformat(), end_date.isoformat()


@aws_retry()
def _get_cost_and_usage(group_key: str, lookback_days: int) -> dict:
    start, end = _default_start_end(lookback_days)
    client = get_ce_client()
    return client.get_cost_and_usage(
        TimePeriod={"Start": start, "End": end},
        Granularity="DAILY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": group_key}],
    )


def get_cost_grouped_by_service(lookback_days: int) -> list[dict]:
    try:
        response = _get_cost_and_usage("SERVICE", lookback_days)
    except (ClientError, BotoCoreError) as error:
        raise translate_aws_error(error, service="Cost Explorer") from error

    records: list[dict] = []
    for bucket in response.get("ResultsByTime", []):
        for group in bucket.get("Groups", []):
            metric = group.get("Metrics", {}).get("UnblendedCost", {})
            records.append(
                {
                    "date": bucket["TimePeriod"]["Start"],
                    "service": group.get("Keys", [""])[0] or "",
                    "region": "",
                    "amount": metric.get("Amount", "0"),
                    "currency": metric.get("Unit", "USD"),
                    "usage_type": "",
                    "account_id": "",
                }
            )
    return records


def get_cost_grouped_by_region(lookback_days: int) -> list[dict]:
    try:
        response = _get_cost_and_usage("REGION", lookback_days)
    except (ClientError, BotoCoreError) as error:
        raise translate_aws_error(error, service="Cost Explorer") from error

    records: list[dict] = []
    for bucket in response.get("ResultsByTime", []):
        for group in bucket.get("Groups", []):
            metric = group.get("Metrics", {}).get("UnblendedCost", {})
            records.append(
                {
                    "date": bucket["TimePeriod"]["Start"],
                    "service": "",
                    "region": group.get("Keys", [""])[0] or "",
                    "amount": metric.get("Amount", "0"),
                    "currency": metric.get("Unit", "USD"),
                    "usage_type": "",
                    "account_id": "",
                }
            )
    return records


@aws_retry()
def get_cost_forecast() -> dict:
    start_date = date.today().isoformat()
    end_date = (date.today() + timedelta(days=30)).isoformat()
    client = get_ce_client()
    try:
        return client.get_cost_forecast(
            TimePeriod={"Start": start_date, "End": end_date},
            Metric="UNBLENDED_COST",
            Granularity="DAILY",
            PredictionIntervalLevel=80,
        )
    except (ClientError, BotoCoreError) as error:
        raise translate_aws_error(error, service="Cost Explorer") from error
