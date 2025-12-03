from pydantic_settings import BaseSettings
from pydantic import Field, computed_field
from typing import List


class Settings(BaseSettings):
    # Bot Configuration
    bot_token: str = Field(..., env="BOT_TOKEN")
    admin_ids_str: str = Field(default="", env="ADMIN_IDS")
    
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Payment System (ЮKassa)
    yookassa_shop_id: str = Field(default="", env="YOOKASSA_SHOP_ID")
    yookassa_secret_key: str = Field(default="", env="YOOKASSA_SECRET_KEY")
    yookassa_oauth_token: str = Field(default="", env="YOOKASSA_OAUTH_TOKEN")  # OAuth токен
    
    # File Storage
    upload_path: str = Field(default="./uploads", env="UPLOAD_PATH")
    max_file_size: int = Field(default=10485760, env="MAX_FILE_SIZE")  # 10MB
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    @computed_field
    @property
    def admin_ids(self) -> List[int]:
        """Parse comma-separated admin IDs from environment variable"""
        if not self.admin_ids_str.strip():
            return []
        return [int(id.strip()) for id in self.admin_ids_str.split(",") if id.strip()]
    
    class Config:
        # Порядок важен: сначала проверяется .env.local (для разработки), 
        # затем .env (продакшн на сервере), затем test.env
        env_file = [".env.local", ".env", "config/test.env"]
        env_file_encoding = "utf-8"
        extra = "ignore"  # Игнорируем дополнительные поля


# Global settings instance
settings = Settings() 