from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    postgres_user: str
    postgres_password: str
    postgres_db: str
    mlflow_tracking_uri: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()