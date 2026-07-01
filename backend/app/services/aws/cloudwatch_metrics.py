from __future__ import annotations

from datetime import UTC, datetime, timedelta

from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.services.aws.client_factory import get_cloudwatch_client
from app.services.aws.common import translate_aws_error
from app.services.aws.retry import aws_retry

EC2_METRICS = ("CPUUtilization", "NetworkIn", "NetworkOut")


@aws_retry()
def _get_metric_data(instance_id: str) -> dict:
    client = get_cloudwatch_client()
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(hours=settings.aws_metric_lookback_hours)

    queries = []
    for metric_name in EC2_METRICS:
        query_id = metric_name.lower().replace("utilization", "util").replace("network", "net")
        queries.append(
            {
                "Id": query_id,
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/EC2",
                        "MetricName": metric_name,
                        "Dimensions": [{"Name": "InstanceId", "Value": instance_id}],
                    },
                    "Period": settings.aws_metric_period_seconds,
                    "Stat": "Average",
                },
                "ReturnData": True,
            }
        )

    return client.get_metric_data(
        MetricDataQueries=queries,
        StartTime=start_time,
        EndTime=end_time,
        ScanBy="TimestampAscending",
    )


def get_instance_metric_samples(instance_id: str) -> list[dict]:
    try:
        response = _get_metric_data(instance_id)
    except (ClientError, BotoCoreError) as error:
        raise translate_aws_error(error, service="CloudWatch") from error

    samples: list[dict] = []
    for result in response.get("MetricDataResults", []):
        label = result.get("Label", "")
        for timestamp, value in zip(result.get("Timestamps", []), result.get("Values", []), strict=False):
            samples.append(
                {
                    "resource_id": instance_id,
                    "metric_name": label,
                    "timestamp": timestamp,
                    "value": value,
                    "unit": result.get("Unit", ""),
                }
            )
    return samples
