from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CloudCost Optimizer"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://cloudcost:cloudcost@postgres:5432/cloudcost"
    jwt_secret_key: str = "replace-with-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    allowed_origin: str = "http://localhost:5173"
    login_rate_limit: str = "5/minute"
    aws_access_key_id: str = "replace-with-your-aws-access-key-id"
    aws_secret_access_key: str = "replace-with-your-aws-secret-access-key"
    aws_region: str = "us-east-1"
    aws_sync_interval_hours: int = 6
    aws_cost_lookback_days: int = 30
    aws_metric_lookback_hours: int = 24
    aws_metric_period_seconds: int = 3600

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("postgresql+asyncpg", "postgresql+psycopg", 1)


settings = Settings()
