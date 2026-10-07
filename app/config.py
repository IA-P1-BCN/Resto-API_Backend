from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite:///./resto.db"
    SECRET_KEY: str = "tu-secreto-aqui"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALLOWED_ORIGINS: str = "http://localhost:5173"
    # Plan §2.2: false en local y CI (el email solo se registra en el log).
    EMAIL_ENABLED: bool = False

settings = Settings()
