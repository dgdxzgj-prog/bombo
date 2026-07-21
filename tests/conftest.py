"""
pytest配置文件
"""
import os
import sys
from datetime import datetime
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置测试环境变量
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/bombo_test"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["LOG_LEVEL"] = "DEBUG"


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    with patch("src.utils.database.Database.get_session") as mock:
        session = MagicMock()
        mock.return_value.__enter__ = MagicMock(return_value=session)
        mock.return_value.__exit__ = MagicMock(return_value=False)
        yield session


@pytest.fixture
def sample_video_data():
    """示例视频数据"""
    return {
        "id": 1,
        "bvid": "BV1234567890",
        "title": "测试视频",
        "author": "测试UP主",
        "channel": "entertainment",
        "keyword": "测试关键词",
        "view_yesterday": 10000,
        "view_today": 15000,
        "growth_rate": 50.0,
        "like_count": 1000,
        "favorite_count": 500,
        "reply_count": 100,
        "pubdate": datetime(2026, 7, 1, 12, 0, 0),
        "cover_url": "https://i0.hdslb.com/test.jpg",
        "status": "monitoring",
        "first_seen": datetime(2026, 7, 1, 10, 0, 0),
        "last_collected": datetime(2026, 7, 16, 8, 0, 0),
        "created_at": datetime(2026, 7, 1, 10, 0, 0),
        "updated_at": datetime(2026, 7, 16, 8, 0, 0),
    }


@pytest.fixture
def sample_channel_config_data():
    """示例赛道配置数据"""
    return {
        "channel_id": "entertainment",
        "channel_name": "娱乐",
        "burst_growth_threshold": 100.0,
        "burst_volume_threshold": 50000,
        "base_growth_threshold": 50.0,
        "base_volume_threshold": 100000,
        "cold_start_threshold": 10000,
        "cold_start_hours": 72,
        "weight_growth": 0.4,
        "weight_volume": 0.3,
        "weight_interaction": 0.3,
        "decline_growth_threshold": 10.0,
        "param_version": 1,
        "effective_time": datetime(2026, 7, 16, 3, 0, 0),
        "sample_size": 1000,
        "is_locked": False,
        "created_at": datetime(2026, 7, 1, 0, 0, 0),
        "updated_at": datetime(2026, 7, 16, 3, 0, 0),
    }
