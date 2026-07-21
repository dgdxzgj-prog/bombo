"""
VideoUpdater单元测试
"""
import pytest
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime

from src.crawlers.video_updater import VideoUpdater
from src.crawlers.bili_data_client import VideoDetail
from src.models.video import Video, VideoStatus


class TestVideoUpdater:
    """VideoUpdater测试类"""

    def setup_method(self):
        """测试前置设置"""
        self.updater = VideoUpdater()

    def test_update_single_video_success(self):
        """测试成功更新单个视频"""
        mock_client = MagicMock()
        mock_monitor_service = MagicMock()

        # mock获取视频详情
        mock_client.get_video_detail.return_value = VideoDetail(
            bvid="BV1234567890",
            title="测试视频",
            author="测试UP主",
            channel="娱乐",
            view_count=15000,
            like_count=1000,
            favorite_count=500,
            reply_count=100,
            pubdate=1234567890,
            cover_url="https://example.com/cover.jpg",
        )

        # mock更新数据库
        mock_monitor_service.update_video_views.return_value = True
        mock_monitor_service.calculate_growth_rate.return_value = 50.0
        mock_monitor_service.roll_views.return_value = True

        updater = VideoUpdater(client=mock_client, monitor_service=mock_monitor_service)
        result = updater._update_single_video("BV1234567890")

        assert result["success"] is True
        mock_monitor_service.update_video_views.assert_called_once_with(
            bvid="BV1234567890",
            view_today=15000,
            like_count=1000,
            favorite_count=500,
            reply_count=100,
        )
        mock_monitor_service.calculate_growth_rate.assert_called_once_with("BV1234567890")
        mock_monitor_service.roll_views.assert_called_once_with("BV1234567890")

    def test_update_single_video_get_detail_failed(self):
        """测试获取视频详情失败"""
        mock_client = MagicMock()
        mock_client.get_video_detail.return_value = None

        updater = VideoUpdater(client=mock_client)
        result = updater._update_single_video("BV1234567890")

        assert result["success"] is False
        assert "Failed to get video detail" in result["error"]

    def test_update_single_video_update_db_failed(self):
        """测试更新数据库失败"""
        mock_client = MagicMock()
        mock_client.get_video_detail.return_value = VideoDetail(
            bvid="BV1234567890",
            title="测试视频",
            author="测试UP主",
            channel="娱乐",
            view_count=15000,
            like_count=1000,
            favorite_count=500,
            reply_count=100,
            pubdate=1234567890,
            cover_url="https://example.com/cover.jpg",
        )

        mock_monitor_service = MagicMock()
        mock_monitor_service.update_video_views.return_value = False

        updater = VideoUpdater(client=mock_client, monitor_service=mock_monitor_service)
        result = updater._update_single_video("BV1234567890")

        assert result["success"] is False
        assert "Failed to update database" in result["error"]

    def test_batch_update_videos(self):
        """测试批量更新视频"""
        mock_client = MagicMock()
        mock_monitor_service = MagicMock()

        # mock获取视频详情
        mock_client.get_video_detail.return_value = VideoDetail(
            bvid="BV1234567890",
            title="测试视频",
            author="测试UP主",
            channel="娱乐",
            view_count=15000,
            like_count=1000,
            favorite_count=500,
            reply_count=100,
            pubdate=1234567890,
            cover_url="https://example.com/cover.jpg",
        )

        mock_monitor_service.update_video_views.return_value = True
        mock_monitor_service.calculate_growth_rate.return_value = 50.0
        mock_monitor_service.roll_views.return_value = True

        updater = VideoUpdater(client=mock_client, monitor_service=mock_monitor_service)

        progress_calls = []
        result = updater.batch_update_videos(
            ["BV1", "BV2", "BV3"],
            progress_callback=lambda current, total: progress_calls.append((current, total))
        )

        assert result["total"] == 3
        assert result["success"] == 3
        assert result["failed"] == 0
        assert len(progress_calls) == 3

    def test_update_all_monitoring_videos(self):
        """测试更新所有监控中的视频"""
        mock_client = MagicMock()
        mock_monitor_service = MagicMock()

        # mock获取监控中的视频列表
        mock_monitor_service.get_all_monitoring_videos.return_value = [
            Video(bvid="BV1", title="视频1", channel="娱乐"),
            Video(bvid="BV2", title="视频2", channel="游戏"),
        ]

        # mock获取视频详情
        mock_client.get_video_detail.return_value = VideoDetail(
            bvid="BV1234567890",
            title="测试视频",
            author="测试UP主",
            channel="娱乐",
            view_count=15000,
            like_count=1000,
            favorite_count=500,
            reply_count=100,
            pubdate=1234567890,
            cover_url="https://example.com/cover.jpg",
        )

        mock_monitor_service.update_video_views.return_value = True
        mock_monitor_service.calculate_growth_rate.return_value = 50.0
        mock_monitor_service.roll_views.return_value = True

        updater = VideoUpdater(client=mock_client, monitor_service=mock_monitor_service)

        result = updater.update_all_monitoring_videos()

        assert result["total"] == 2
        assert result["success"] == 2
        assert result["failed"] == 0

    def test_update_videos_by_channel(self):
        """测试更新指定赛道的视频"""
        mock_client = MagicMock()
        mock_monitor_service = MagicMock()

        # mock获取指定赛道的视频
        mock_monitor_service.get_videos_by_channel.return_value = [
            Video(bvid="BV1", title="视频1", channel="娱乐"),
        ]

        # mock获取视频详情
        mock_client.get_video_detail.return_value = VideoDetail(
            bvid="BV1234567890",
            title="测试视频",
            author="测试UP主",
            channel="娱乐",
            view_count=15000,
            like_count=1000,
            favorite_count=500,
            reply_count=100,
            pubdate=1234567890,
            cover_url="https://example.com/cover.jpg",
        )

        mock_monitor_service.update_video_views.return_value = True
        mock_monitor_service.calculate_growth_rate.return_value = 50.0
        mock_monitor_service.roll_views.return_value = True

        updater = VideoUpdater(client=mock_client, monitor_service=mock_monitor_service)

        result = updater.update_videos_by_channel("娱乐")

        assert result["total"] == 1
        assert result["success"] == 1
        assert result["channel"] == "娱乐"

    def test_progress_callback(self):
        """测试进度回调"""
        mock_client = MagicMock()
        mock_monitor_service = MagicMock()

        mock_monitor_service.get_all_monitoring_videos.return_value = [
            Video(bvid="BV1", title="视频1", channel="娱乐"),
            Video(bvid="BV2", title="视频2", channel="游戏"),
        ]

        mock_client.get_video_detail.return_value = VideoDetail(
            bvid="BV1234567890",
            title="测试视频",
            author="测试UP主",
            channel="娱乐",
            view_count=15000,
            like_count=1000,
            favorite_count=500,
            reply_count=100,
            pubdate=1234567890,
            cover_url="https://example.com/cover.jpg",
        )

        mock_monitor_service.update_video_views.return_value = True
        mock_monitor_service.calculate_growth_rate.return_value = 50.0
        mock_monitor_service.roll_views.return_value = True

        updater = VideoUpdater(client=mock_client, monitor_service=mock_monitor_service)

        progress = []
        updater.update_all_monitoring_videos(
            progress_callback=lambda current, total: progress.append((current, total))
        )

        assert len(progress) == 2
        assert progress[0] == (1, 2)
        assert progress[1] == (2, 2)

    def test_update_with_empty_video_list(self):
        """测试空视频列表"""
        mock_monitor_service = MagicMock()
        mock_monitor_service.get_all_monitoring_videos.return_value = []

        updater = VideoUpdater(monitor_service=mock_monitor_service)
        result = updater.update_all_monitoring_videos()

        assert result["total"] == 0
        assert result["success"] == 0
        assert result["failed"] == 0

    def test_update_error_handling(self):
        """测试错误处理"""
        mock_client = MagicMock()
        mock_monitor_service = MagicMock()

        mock_monitor_service.get_all_monitoring_videos.return_value = [
            Video(bvid="BV1", title="视频1", channel="娱乐"),
        ]

        # 模拟获取详情时抛出异常
        mock_client.get_video_detail.side_effect = Exception("Network error")

        updater = VideoUpdater(client=mock_client, monitor_service=mock_monitor_service)
        result = updater.update_all_monitoring_videos()

        assert result["total"] == 1
        assert result["success"] == 0
        assert result["failed"] == 1
        assert "Network error" in result["errors"][0]
