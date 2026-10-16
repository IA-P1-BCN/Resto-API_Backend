from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = "sqlite:///./resto.db"
    JWT_SECRET_KEY: str = "dev-secret-cambiar-en-produccion-0000"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    ALLOWED_ORIGINS: str = "http://localhost:5173"
    EMAIL_ENABLED: bool = False
    BREVO_API_KEY: str = ""
    MAIL_FROM: str = ""
    FRONTEND_URL: str = "http://localhost:5173"
    PASSWORD_TOKEN_EXPIRE_HOURS: int = 48
    EMAIL_VERIFY_EXPIRE_HOURS: int = 48
    PASSWORD_RESET_EXPIRE_HOURS: int = 1
    TOKEN_RESEND_COOLDOWN_SECONDS: int = 60
    TOTP_ENCRYPTION_KEY: str = ""
    STATS_CACHE_TTL: int = 60
    LOGIN_MAX_ATTEMPTS: int = Field(default=5, ge=1)
    LOGIN_WINDOW_MINUTES: int = Field(default=15, ge=1)
    CLIENT_IP_HEADER: str = ""
    RESTAURANT_TIMEZONE: str = "Europe/Madrid"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    KEEP_AWAKE_ENABLED: bool = False
    KEEP_AWAKE_URL: str = ""
    KEEP_AWAKE_MINUTES: int = 10

settings = Settings()
