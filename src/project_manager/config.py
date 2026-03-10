from typing import Optional

from pydantic_settings import BaseSettings


class ProjectManagerSettings(BaseSettings):

    DATA_PATH: str = "/data"

    GITHUB_APP_ID: Optional[str] = None
    GITHUB_TOKEN: str

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # Database Configuration
    DATABASE_URL: str = "sqlite:///polycode.db"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = ProjectManagerSettings()  # pyright:ignore # ty:ignore
