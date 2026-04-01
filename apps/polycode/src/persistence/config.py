from pydantic_settings import BaseSettings, SettingsConfigDict


class PersistenceSettings(BaseSettings):
    # Database Configuration
    DATABASE_URL: str = "sqlite:///polycode.db"

    model_config = SettingsConfigDict(extra="ignore", env_file=".env", case_sensitive=True)


settings = PersistenceSettings()  # pyright:ignore
