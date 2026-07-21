"""
配置管理模块
"""
import os
from typing import Optional

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """应用配置"""

    model_config = {"populate_by_name": True}

    # 应用配置
    APP_NAME: str = "BOMBO"
    DEBUG: bool = False
    ENV: str = "development"
    SECRET_KEY: str = "your-secret-key-here"

    # 数据库配置
    DATABASE_URL: str = "postgresql://bombo:bombo123@localhost:5432/bombo"
    DATABASE_POOL_SIZE: int = 10

    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600

    # B站爬虫配置
    BILI_COOKIE: Optional[str] = None
    BILI_WBI_KEY: Optional[str] = None
    CRAWLER_PROXY_POOL: Optional[str] = None

    # AI模型配置
    ARK_API_KEY: str = ""
    DOUBAO_MODEL: str = "doubao-seed-2-0-lite-260428"

    # 日志配置
    LOG_LEVEL: str = "INFO"


def _get_settings() -> Settings:
    """从环境变量加载配置"""
    return Settings(
        APP_NAME=os.getenv("APP_NAME", "BOMBO"),
        DEBUG=os.getenv("DEBUG", "false").lower() == "true",
        ENV=os.getenv("ENV", "development"),
        SECRET_KEY=os.getenv("SECRET_KEY", "your-secret-key-here"),
        DATABASE_URL=os.getenv("DATABASE_URL", "postgresql://bombo:bombo123@localhost:5432/bombo"),
        DATABASE_POOL_SIZE=int(os.getenv("DATABASE_POOL_SIZE", "10")),
        REDIS_URL=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        REDIS_CACHE_TTL=int(os.getenv("REDIS_CACHE_TTL", "3600")),
        BILI_COOKIE=os.getenv("BILI_COOKIE"),
        BILI_WBI_KEY=os.getenv("BILI_WBI_KEY"),
        CRAWLER_PROXY_POOL=os.getenv("CRAWLER_PROXY_POOL"),
        ARK_API_KEY=os.getenv("ARK_API_KEY", ""),
        DOUBAO_MODEL=os.getenv("DOUBAO_MODEL", "doubao-seed-2-0-lite-260428"),
        LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
    )


settings = _get_settings()
