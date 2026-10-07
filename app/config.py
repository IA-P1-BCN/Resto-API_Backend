from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = "sqlite:///./resto.db"
    SECRET_KEY: str = "tu-secreto-aqui"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALLOWED_ORIGINS: str = "http://localhost:5173"

settings = Settings()
