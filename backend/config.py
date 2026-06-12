from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str
    JWT_SECRET_KEY: str
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DATABASE_URL: str = "sqlite:///./aws_ops.db"
    SYNC_INTERVAL_MINUTES: int = 15
    CERT_CHECK_INTERVAL_HOURS: int = 6

    class Config:
        env_file = ".env"


settings = Settings()
