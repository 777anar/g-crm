from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"

    database_url: str = "sqlite:///./dev.db"

    jwt_secret_key: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    redis_url: str = "redis://localhost:6379/0"

    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_storage_bucket: str = "g-erp-documents"

    local_storage_dir: str = "./storage_data"

    cors_allow_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
