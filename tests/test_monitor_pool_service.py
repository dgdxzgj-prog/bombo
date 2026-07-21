"""
MonitorPoolService单元测试
"""
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from src.models.video import Video, VideoStatus
from src.services.monitor_pool_service import MonitorPoolService


class TestMonitorPoolService:
    """MonitorPoolService测试类"""

    def setup_method(self):
        """测试前置设置"""
        self.service = MonitorPoolService()

    @patch("src.services.monitor_pool_service.get_db_session")
    def test_add_video_success(self, mock_get_session):
        """测试成功添加视频"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # 模拟不存在重复
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        video = Video(
            bvid="BV1234567890",
            title="测试视频",
            author="测试UP主",
            channel="entertainment",
        )

        with pytest.raises(Exception):
            self.service.add_video(video)

    @patch("src.services.monitor_pool_service.get_db_session")
    def test_add_video_duplicate_bvid(self, mock_get_session):
        """测试重复bvid拒绝"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # 模拟已存在
        existing_video = Video(bvid="BV1234567890", title="已存在视频")
        mock_session.execute.return_value.scalar_one_or_none.return_value = existing_video

        video = Video(bvid="BV1234567890", title="新视频")

        with pytest.raises(ValueError, match="already exists"):
            self.service.add_video(video)

    @patch("src.services.monitor_pool_service.get_db_session")
    def test_get_video_by_bvid_found(self, mock_get_session):
        """测试根据bvid查询到视频"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # fetchone returns a tuple matching the SQL query
        mock_session.execute.return_value.fetchone.return_value = (
            1, "BV1234567890", "测试视频", "测试UP主", "entertainment",
            "", 10000, 15000, 50.0, 0, 0, 0, None, None,
            VideoStatus.MONITORING.value, None, None, datetime.now(), datetime.now()
        )

        result = self.service.get_video_by_bvid("BV1234567890")

        assert result is not None
        assert result.bvid == "BV1234567890"
        assert result.title == "测试视频"
        assert result.growth_rate == 50.0

    @patch("src.services.monitor_pool_service.get_db_session")
    def test_get_video_by_bvid_not_found(self, mock_get_session):
        """测试根据bvid查询不到视频"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_session.execute.return_value.fetchone.return_value = None

        result = self.service.get_video_by_bvid("BV0000000000")

        assert result is None

    @patch("src.services.monitor_pool_service.get_db_session")
    def test_calculate_growth_rate_normal(self, mock_get_session):
        """测试正常增速计算"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # calculate_growth_rate calls get_video_by_bvid which uses fetchone with full tuple
        mock_session.execute.return_value.fetchone.return_value = (
            1, "BV1234567890", "测试视频", "测试UP主", "entertainment",
            "", 10000, 15000, 0.0, 0, 0, 0, None, None,
            VideoStatus.MONITORING.value, None, None, datetime.now(), datetime.now()
        )

        result = self.service.calculate_growth_rate("BV1234567890")

        assert result == 50.0

    @patch("src.services.monitor_pool_service.get_db_session")
    def test_calculate_growth_rate_zero_yesterday(self, mock_get_session):
        """测试昨日播放量为0时的增速计算"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_session.execute.return_value.fetchone.return_value = (
            1, "BV1234567890", "测试视频", "测试UP主", "entertainment",
            "", 0, 15000, 0.0, 0, 0, 0, None, None,
            VideoStatus.MONITORING.value, None, None, datetime.now(), datetime.now()
        )

        result = self.service.calculate_growth_rate("BV1234567890")

        assert result == 0.0

    @patch("src.services.monitor_pool_service.get_db_session")
    def test_calculate_growth_rate_video_not_found(self, mock_get_session):
        """测试视频不存在时的增速计算"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_session.execute.return_value.fetchone.return_value = None

        result = self.service.calculate_growth_rate("BV0000000000")

        assert result is None

    @patch("src.services.monitor_pool_service.get_db_session")
    def test_roll_views_success(self, mock_get_session):
        """测试成功滚动播放数据"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        video = Video(
            bvid="BV1234567890",
            view_yesterday=10000,
            view_today=15000,
        )

        # roll_views calls get_video_by_bvid which uses fetchone
        mock_session.execute.return_value.fetchone.return_value = (
            1, "BV1234567890", "测试视频", "测试UP主", "entertainment",
            "", 10000, 15000, 0.0, 0, 0, 0, None, None,
            VideoStatus.MONITORING.value, None, None, datetime.now(), datetime.now()
        )

        result = self.service.roll_views("BV1234567890")

        assert result is True

    @patch("src.services.monitor_pool_service.get_db_session")
    def test_roll_views_video_not_found(self, mock_get_session):
        """测试视频不存在时的滚动"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_session.execute.return_value.fetchone.return_value = None

        result = self.service.roll_views("BV0000000000")

        assert result is False

    @patch("src.services.monitor_pool_service.get_db_session")
    def test_update_video_status(self, mock_get_session):
        """测试更新视频状态"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = self.service.update_video_status("BV1234567890", VideoStatus.FEATURED)

        assert result is True

    @patch("src.services.monitor_pool_service.get_db_session")
    def test_update_video_views(self, mock_get_session):
        """测试更新播放数据"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = self.service.update_video_views(
            bvid="BV1234567890",
            view_today=20000,
            like_count=1500,
        )

        assert result is True

    @patch("src.services.monitor_pool_service.get_db_session")
    def test_delete_video_success(self, mock_get_session):
        """测试删除视频成功"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = self.service.delete_video("BV1234567890")

        assert result is True

    @patch("src.services.monitor_pool_service.get_db_session")
    def test_delete_video_not_found(self, mock_get_session):
        """测试删除不存在的视频"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = self.service.delete_video("BV0000000000")

        assert result is False

    def test_video_status_transitions(self):
        """测试视频状态流转"""
        video = Video(bvid="BV1234567890", status=VideoStatus.MONITORING)

        # monitoring -> featured
        assert video.status == VideoStatus.MONITORING
        video.status = VideoStatus.FEATURED
        assert video.status == VideoStatus.FEATURED

        # featured -> declined
        video.status = VideoStatus.DECLINED
        assert video.status == VideoStatus.DECLINED

    def test_growth_rate_calculation_edge_cases(self):
        """测试增速计算边界情况"""
        # 昨日播放量为1，今日播放量为2，增速应该是100%
        video = Video(bvid="BV1234567890", view_yesterday=1, view_today=2)
        assert video.calculate_growth_rate() == 100.0

        # 昨日播放量很大，今日播放量相同，增速应该是0%
        video = Video(bvid="BV1234567890", view_yesterday=1000000, view_today=1000000)
        assert video.calculate_growth_rate() == 0.0

        # 测试精度
        video = Video(bvid="BV1234567890", view_yesterday=33333, view_today=33334)
        growth = video.calculate_growth_rate()
        assert growth == 0.0  # (1/33333)*100 = 0.003, 保留两位小数为0.00
