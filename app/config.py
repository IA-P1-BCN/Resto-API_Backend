from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite:///./resto.db"
    JWT_SECRET_KEY: str = "dev-secret-cambiar-en-produccion-0000"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    ALLOWED_ORIGINS: str = "http://localhost:5173"
    # Plan §2.2: false en local y CI (el email solo se registra en el log).
    EMAIL_ENABLED: bool = False

settings = Settings()
