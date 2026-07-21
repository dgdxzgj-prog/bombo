"""
ChannelConfig模型单元测试
"""
from datetime import datetime

import pytest

from src.models.channel import ChannelConfig


class TestChannelConfigModel:
    """ChannelConfig模型测试类"""

    def test_channel_config_creation(self):
        """测试赛道配置对象创建"""
        config = ChannelConfig(
            channel_id="entertainment",
            channel_name="娱乐",
        )

        assert config.channel_id == "entertainment"
        assert config.channel_name == "娱乐"
        assert config.burst_growth_threshold == 0.0
        assert config.burst_volume_threshold == 0
        assert config.is_locked is False
        assert config.param_version == 1

    def test_channel_config_with_params(self):
        """测试带参数的赛道配置"""
        config = ChannelConfig(
            channel_id="gaming",
            channel_name="游戏",
            burst_growth_threshold=100.0,
            burst_volume_threshold=50000,
            base_growth_threshold=50.0,
            base_volume_threshold=100000,
            cold_start_threshold=10000,
            cold_start_hours=72,
            weight_growth=0.4,
            weight_volume=0.3,
            weight_interaction=0.3,
            decline_growth_threshold=10.0,
        )

        assert config.burst_growth_threshold == 100.0
        assert config.burst_volume_threshold == 50000
        assert config.base_growth_threshold == 50.0
        assert config.base_volume_threshold == 100000
        assert config.cold_start_threshold == 10000
        assert config.cold_start_hours == 72
        assert config.weight_growth == 0.4
        assert config.weight_volume == 0.3
        assert config.weight_interaction == 0.3
        assert config.decline_growth_threshold == 10.0

    def test_to_dict(self):
        """测试转换为字典"""
        config = ChannelConfig(
            channel_id="entertainment",
            channel_name="娱乐",
            burst_growth_threshold=100.0,
            burst_volume_threshold=50000,
            is_locked=False,
            param_version=1,
        )

        data = config.to_dict()

        assert data["channel_id"] == "entertainment"
        assert data["channel_name"] == "娱乐"
        assert data["burst_growth_threshold"] == 100.0
        assert data["burst_volume_threshold"] == 50000
        assert data["is_locked"] is False
        assert data["param_version"] == 1

    def test_from_dict(self):
        """测试从字典创建对象"""
        data = {
            "channel_id": "gaming",
            "channel_name": "游戏",
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
            "param_version": 2,
            "effective_time": "2026-07-16T03:00:00",
            "sample_size": 1000,
            "is_locked": True,
            "created_at": "2026-07-01T00:00:00",
            "updated_at": "2026-07-16T03:00:00",
        }

        config = ChannelConfig.from_dict(data)

        assert config.channel_id == "gaming"
        assert config.channel_name == "游戏"
        assert config.burst_growth_threshold == 100.0
        assert config.burst_volume_threshold == 50000
        assert config.is_locked is True
        assert config.param_version == 2
        assert config.sample_size == 1000

    def test_channel_config_default_values(self):
        """测试默认值"""
        config = ChannelConfig(channel_id="test")

        assert config.channel_name == ""
        assert config.burst_growth_threshold == 0.0
        assert config.burst_volume_threshold == 0
        assert config.base_growth_threshold == 0.0
        assert config.base_volume_threshold == 0
        assert config.cold_start_threshold == 0
        assert config.cold_start_hours == 72
        assert config.weight_growth == 0.4
        assert config.weight_volume == 0.3
        assert config.weight_interaction == 0.3
        assert config.decline_growth_threshold == 0.0
        assert config.param_version == 1
        assert config.sample_size == 0
        assert config.is_locked is False

    def test_weights_sum(self):
        """测试权重总和"""
        config = ChannelConfig(
            channel_id="test",
            weight_growth=0.4,
            weight_volume=0.3,
            weight_interaction=0.3,
        )

        total_weight = config.weight_growth + config.weight_volume + config.weight_interaction
        assert total_weight == 1.0
