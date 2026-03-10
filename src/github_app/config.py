from typing import Optional

from pydantic_settings import BaseSettings


class GitHubAppSettings(BaseSettings):
    # GitHub App Configuration
    GITHUB_APP_ID: str = ""
    GITHUB_APP_PRIVATE_KEY: str = ""
    GITHUB_APP_WEBHOOK_SECRET: str = ""
    GITHUB_APP_NAME: str = "Polycode GitHub App"

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # Database Configuration
    DATABASE_URL: str = "sqlite:///polycode.db"

    # Webhook Server Configuration
    WEBHOOK_HOST: str = "0.0.0.0"
    WEBHOOK_PORT: int = 8000
    WEBHOOK_PATH: str = "/webhook/github"
    WEBHOOK_URL: Optional[str] = None

    # GitHub API Configuration
    GITHUB_API_URL: str = "https://api.github.com"

    # Celery Configuration
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = GitHubAppSettings()
