from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://chat:chatpass@localhost:5432/chatroom"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"

    class Config:
        env_file = ".env"


settings = Settings()
