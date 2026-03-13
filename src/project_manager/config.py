from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class ProjectManagerSettings(BaseSettings):

    DATA_PATH: str = "/data"

    GITHUB_APP_ID: Optional[str] = None
    GITHUB_TOKEN: str

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    PROJECT_PROVIDER: Optional[str] = None
    REPO_OWNER: Optional[str] = None
    REPO_NAME: Optional[str] = None
    PROJECT_IDENTIFIER: Optional[str] = None

    # Database Configuration
    DATABASE_URL: str = "sqlite:///polycode.db"

    model_config = SettingsConfigDict(
        extra="ignore", env_file=".env", case_sensitive=True
    )


settings = ProjectManagerSettings()  # pyright:ignore # ty:ignore
