"""
ChannelConfigService单元测试
"""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.models.channel import ChannelConfig
from src.services.channel_config_service import ChannelConfigService


class TestChannelConfigService:
    """ChannelConfigService测试类"""

    def setup_method(self):
        """测试前置设置"""
        self.service = ChannelConfigService()

    @patch("src.services.channel_config_service.get_db_session")
    def test_add_channel_success(self, mock_get_session):
        """测试成功添加赛道配置"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        config = ChannelConfig(
            channel_id="test_channel",
            channel_name="测试赛道",
        )

        with pytest.raises(Exception):
            self.service.add_channel(config)

    @patch("src.services.channel_config_service.get_db_session")
    def test_add_channel_duplicate(self, mock_get_session):
        """测试添加重复赛道配置"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        existing_config = ChannelConfig(channel_id="test_channel")
        mock_session.execute.return_value.scalar_one_or_none.return_value = existing_config

        config = ChannelConfig(channel_id="test_channel", channel_name="新配置")

        with pytest.raises(ValueError, match="already exists"):
            self.service.add_channel(config)

    @patch("src.services.channel_config_service.get_db_session")
    def test_get_channel_by_id_found(self, mock_get_session):
        """测试根据channel_id查询到配置"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # fetchone returns tuple matching the SQL query
        mock_session.execute.return_value.fetchone.return_value = (
            "entertainment", "娱乐", 100.0, 50000, 50.0, 100000,
            10000, 72, 0.4, 0.3, 0.3, 10.0, 1, None, 0, False,
            datetime.now(), datetime.now()
        )

        result = self.service.get_channel_by_id("entertainment")

        assert result is not None
        assert result.channel_id == "entertainment"
        assert result.burst_growth_threshold == 100.0

    @patch("src.services.channel_config_service.get_db_session")
    def test_get_channel_by_id_not_found(self, mock_get_session):
        """测试根据channel_id查询不到配置"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_session.execute.return_value.fetchone.return_value = None

        result = self.service.get_channel_by_id("non_existent")

        assert result is None

    @patch("src.services.channel_config_service.get_db_session")
    def test_get_all_channels(self, mock_get_session):
        """测试获取所有赛道配置"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # fetchall returns list of tuples
        mock_session.execute.return_value.fetchall.return_value = [
            ("entertainment", "娱乐", 100.0, 50000, 50.0, 100000,
             10000, 72, 0.4, 0.3, 0.3, 10.0, 1, None, 0, False,
             datetime.now(), datetime.now()),
            ("gaming", "游戏", 100.0, 50000, 50.0, 100000,
             10000, 72, 0.4, 0.3, 0.3, 10.0, 1, None, 0, False,
             datetime.now(), datetime.now()),
            ("technology", "科技", 100.0, 50000, 50.0, 100000,
             10000, 72, 0.4, 0.3, 0.3, 10.0, 1, None, 0, False,
             datetime.now(), datetime.now()),
        ]

        result = self.service.get_all_channels()

        assert len(result) == 3
        assert result[0].channel_id == "entertainment"
        assert result[1].channel_id == "gaming"
        assert result[2].channel_id == "technology"

    @patch("src.services.channel_config_service.get_db_session")
    def test_lock_channel(self, mock_get_session):
        """测试锁定赛道"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = self.service.lock_channel("entertainment")

        assert result is True

    @patch("src.services.channel_config_service.get_db_session")
    def test_unlock_channel(self, mock_get_session):
        """测试解锁赛道"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = self.service.unlock_channel("entertainment")

        assert result is True

    @patch("src.services.channel_config_service.get_db_session")
    def test_update_channel_params(self, mock_get_session):
        """测试更新赛道参数"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = self.service.update_channel_params(
            channel_id="entertainment",
            burst_growth_threshold=150.0,
            burst_volume_threshold=80000,
        )

        assert result is True

    @patch("src.services.channel_config_service.get_db_session")
    def test_increment_version(self, mock_get_session):
        """测试增加参数版本号"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        existing_config = ChannelConfig(
            channel_id="entertainment",
            param_version=1,
        )
        mock_session.execute.return_value.scalar_one_or_none.return_value = existing_config

        mock_result = MagicMock()
        mock_result.rowcount = 1
        # 第二次execute调用
        mock_session.execute.return_value = mock_result

        result = self.service.increment_version("entertainment")

        assert result is True

    @patch("src.services.channel_config_service.get_db_session")
    def test_delete_channel_success(self, mock_get_session):
        """测试删除赛道成功"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = self.service.delete_channel("entertainment")

        assert result is True

    @patch("src.services.channel_config_service.get_db_session")
    def test_delete_channel_not_found(self, mock_get_session):
        """测试删除不存在的赛道"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = self.service.delete_channel("non_existent")

        assert result is False

    @patch("src.services.channel_config_service.get_db_session")
    def test_get_unlocked_channels(self, mock_get_session):
        """测试获取未锁定赛道"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # fetchall returns list of tuples
        mock_session.execute.return_value.fetchall.return_value = [
            ("entertainment", "娱乐", 100.0, 50000, 50.0, 100000,
             10000, 72, 0.4, 0.3, 0.3, 10.0, 1, None, 0, False,
             datetime.now(), datetime.now()),
            ("gaming", "游戏", 100.0, 50000, 50.0, 100000,
             10000, 72, 0.4, 0.3, 0.3, 10.0, 1, None, 0, False,
             datetime.now(), datetime.now()),
        ]

        result = self.service.get_unlocked_channels()

        assert len(result) == 2
        for config in result:
            assert config.is_locked is False

    def test_channel_config_model_methods(self):
        """测试ChannelConfig模型方法"""
        config = ChannelConfig(
            channel_id="test",
            channel_name="测试",
            burst_growth_threshold=100.0,
            burst_volume_threshold=50000,
        )

        data = config.to_dict()
        assert data["channel_id"] == "test"
        assert data["burst_growth_threshold"] == 100.0

        restored = ChannelConfig.from_dict(data)
        assert restored.channel_id == config.channel_id
        assert restored.burst_growth_threshold == config.burst_growth_threshold
