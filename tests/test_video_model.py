"""
Video模型单元测试
"""
from datetime import datetime
from unittest.mock import patch

import pytest

from src.models.video import Video, VideoStatus


class TestVideoModel:
    """Video模型测试类"""

    def test_video_creation(self):
        """测试视频对象创建"""
        video = Video(
            bvid="BV1234567890",
            title="测试视频",
            author="测试UP主",
            channel="entertainment",
        )

        assert video.bvid == "BV1234567890"
        assert video.title == "测试视频"
        assert video.author == "测试UP主"
        assert video.channel == "entertainment"
        assert video.status == VideoStatus.MONITORING
        assert video.view_yesterday == 0
        assert video.view_today == 0
        assert video.growth_rate == 0.0

    def test_calculate_growth_rate_normal(self):
        """测试正常情况下的增速计算"""
        video = Video(
            bvid="BV1234567890",
            view_yesterday=10000,
            view_today=15000,
        )

        growth_rate = video.calculate_growth_rate()
        assert growth_rate == 50.0

    def test_calculate_growth_rate_zero_yesterday(self):
        """测试昨日播放量为0时的增速计算"""
        video = Video(
            bvid="BV1234567890",
            view_yesterday=0,
            view_today=15000,
        )

        growth_rate = video.calculate_growth_rate()
        assert growth_rate == 0.0

    def test_calculate_growth_rate_negative(self):
        """测试播放量下降时的增速计算"""
        video = Video(
            bvid="BV1234567890",
            view_yesterday=10000,
            view_today=5000,
        )

        growth_rate = video.calculate_growth_rate()
        assert growth_rate == -50.0

    def test_calculate_growth_rate_precision(self):
        """测试增速计算精度（保留两位小数）"""
        video = Video(
            bvid="BV1234567890",
            view_yesterday=33333,
            view_today=44444,
        )

        growth_rate = video.calculate_growth_rate()
        # (44444 - 33333) / 33333 * 100 = 33.33
        assert growth_rate == 33.33

    def test_roll_views(self):
        """测试播放数据滚动"""
        video = Video(
            bvid="BV1234567890",
            view_yesterday=10000,
            view_today=15000,
        )

        video.roll_views()

        assert video.view_yesterday == 15000
        assert video.view_today == 0

    def test_is_published_within_hours_true(self):
        """测试发布时间在指定小时内"""
        video = Video(
            bvid="BV1234567890",
            pubdate=datetime(2026, 7, 16, 10, 0, 0),  # 2小时前
        )

        # 假设当前时间是 2026-07-16 12:00:00
        with patch("src.models.video.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 7, 16, 12, 0, 0)
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            result = video.is_published_within_hours(72)
            assert result is True

    def test_is_published_within_hours_false(self):
        """测试发布时间超过指定小时"""
        video = Video(
            bvid="BV1234567890",
            pubdate=datetime(2026, 7, 1, 10, 0, 0),  # 15天前
        )

        with patch("src.models.video.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 7, 16, 12, 0, 0)
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            result = video.is_published_within_hours(72)
            assert result is False

    def test_is_published_within_hours_no_pubdate(self):
        """测试无发布时间的情况"""
        video = Video(bvid="BV1234567890", pubdate=None)

        result = video.is_published_within_hours(72)
        assert result is False

    def test_to_dict(self):
        """测试转换为字典"""
        video = Video(
            id=1,
            bvid="BV1234567890",
            title="测试视频",
            author="测试UP主",
            channel="entertainment",
            view_yesterday=10000,
            view_today=15000,
            growth_rate=50.0,
            status=VideoStatus.MONITORING,
        )

        data = video.to_dict()

        assert data["id"] == 1
        assert data["bvid"] == "BV1234567890"
        assert data["title"] == "测试视频"
        assert data["status"] == "monitoring"
        assert data["growth_rate"] == 50.0

    def test_from_dict(self):
        """测试从字典创建对象"""
        data = {
            "id": 1,
            "bvid": "BV1234567890",
            "title": "测试视频",
            "author": "测试UP主",
            "channel": "entertainment",
            "view_yesterday": 10000,
            "view_today": 15000,
            "growth_rate": 50.0,
            "like_count": 1000,
            "favorite_count": 500,
            "reply_count": 100,
            "pubdate": "2026-07-01T12:00:00",
            "cover_url": "https://i0.hdslb.com/test.jpg",
            "status": "featured",
            "first_seen": "2026-07-01T10:00:00",
            "last_collected": "2026-07-16T08:00:00",
            "created_at": "2026-07-01T10:00:00",
            "updated_at": "2026-07-16T08:00:00",
        }

        video = Video.from_dict(data)

        assert video.id == 1
        assert video.bvid == "BV1234567890"
        assert video.title == "测试视频"
        assert video.status == VideoStatus.FEATURED
        assert video.view_today == 15000

    def test_video_status_enum(self):
        """测试视频状态枚举"""
        assert VideoStatus.MONITORING.value == "monitoring"
        assert VideoStatus.FEATURED.value == "featured"
        assert VideoStatus.DECLINED.value == "declined"

    def test_video_default_values(self):
        """测试默认值"""
        video = Video(bvid="BV1234567890")

        assert video.title == ""
        assert video.author == ""
        assert video.channel == ""
        assert video.keyword == ""
        assert video.view_yesterday == 0
        assert video.view_today == 0
        assert video.growth_rate == 0.0
        assert video.like_count == 0
        assert video.favorite_count == 0
        assert video.reply_count == 0
        assert video.pubdate is None
        assert video.cover_url is None
        assert video.status == VideoStatus.MONITORING
        assert video.id is None
