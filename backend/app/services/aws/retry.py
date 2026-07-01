from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


def aws_retry():
    return retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(Exception),
    )
