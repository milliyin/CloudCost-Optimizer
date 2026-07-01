class AWSServiceError(Exception):
    def __init__(self, message: str, *, code: str | None = None, service: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.service = service
