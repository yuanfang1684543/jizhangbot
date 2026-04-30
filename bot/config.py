import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str = ""
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/accounting_bot"
    WEBHOOK_URL: str = ""
    ADMIN_USER_IDS: str = ""

    @property
    def admin_ids(self) -> list[int]:
        return [int(uid) for uid in self.ADMIN_USER_IDS.split(",") if uid.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
