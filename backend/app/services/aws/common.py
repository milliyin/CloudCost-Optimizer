from __future__ import annotations

from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

from app.services.aws.errors import AWSServiceError


def translate_aws_error(error: Exception, *, service: str) -> AWSServiceError:
    if isinstance(error, (NoCredentialsError, PartialCredentialsError)):
        return AWSServiceError(
            "AWS credentials are missing or incomplete. Check the local .env file for the IAM access key and secret.",
            code=error.__class__.__name__,
            service=service,
        )

    if isinstance(error, ClientError):
        code = error.response.get("Error", {}).get("Code", "Unknown")
        message = error.response.get("Error", {}).get("Message", "AWS request failed")

        if code in {"AccessDenied", "AccessDeniedException", "UnauthorizedOperation"}:
            return AWSServiceError(
                "AWS denied access. Check the IAM policy on cloudcost-app, and if you expected Billing console access also confirm Activate IAM Access is enabled for the account.",
                code=code,
                service=service,
            )
        if code in {"UnrecognizedClientException", "InvalidClientTokenId", "SignatureDoesNotMatch", "AuthFailure"}:
            return AWSServiceError(
                "AWS rejected the credentials. Double-check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in the local .env file.",
                code=code,
                service=service,
            )
        if code in {"ExpiredToken", "ExpiredTokenException"}:
            return AWSServiceError(
                "The AWS credentials have expired. Create a fresh access key for the IAM user and update the local .env file.",
                code=code,
                service=service,
            )
        if code in {"LimitExceededException", "TooManyRequestsException", "Throttling", "ThrottlingException", "RequestLimitExceeded"}:
            return AWSServiceError(
                "AWS is throttling requests right now. Please retry the sync shortly.",
                code=code,
                service=service,
            )
        if code in {"DataUnavailableException", "BillExpirationException"}:
            return AWSServiceError(
                "Cost Explorer data is not available yet. If Cost Explorer was just enabled, AWS may still be preparing billing data for up to about 24 hours.",
                code=code,
                service=service,
            )
        if code == "ResourceNotFoundException":
            return AWSServiceError(
                "The requested AWS billing view or resource was not found. Check the account setup and region.",
                code=code,
                service=service,
            )

        return AWSServiceError(f"{service} request failed: {message}", code=code, service=service)

    return AWSServiceError(f"{service} request failed: {error}", code=error.__class__.__name__, service=service)
