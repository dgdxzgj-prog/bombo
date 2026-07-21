"""
爬虫模块单元测试
"""
import pytest
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime

from src.crawlers.anti_crawler import AntiCrawlerConfig, AntiCrawlerManager
from src.crawlers.bili_data_client import (
    BiliDataClient, VideoSearchResult, VideoDetail, VideoUpdateResult
)
from src.crawlers.video_discoverer import VideoDiscoverer
from src.models.video import Video, VideoStatus


class TestAntiCrawler:
    """反爬策略测试类"""

    def setup_method(self):
        """测试前置设置"""
        self.config = AntiCrawlerConfig(
            min_delay=1.0,
            max_delay=2.0,
            max_retries=3,
        )
        self.manager = AntiCrawlerManager(self.config)

    def test_get_random_user_agent(self):
        """测试获取随机User-Agent"""
        ua = self.manager.get_random_user_agent()
        assert ua in self.config.user_agents

    def test_get_random_user_agent_multiple(self):
        """测试多次获取User-Agent是否都在列表中"""
        for _ in range(10):
            ua = self.manager.get_random_user_agent()
            assert ua in self.config.user_agents

    def test_get_random_delay(self):
        """测试获取随机延时范围"""
        for _ in range(10):
            delay = self.manager.get_random_delay()
            assert self.config.min_delay <= delay <= self.config.max_delay

    def test_get_headers(self):
        """测试获取请求头"""
        headers = self.manager.get_headers()
        assert "User-Agent" in headers
        assert headers["User-Agent"] in self.config.user_agents
        assert "Accept" in headers
        assert "Referer" in headers

    def test_get_random_proxy_with_pool(self):
        """测试从代理池获取代理"""
        config = AntiCrawlerConfig(
            proxy_pool=["http://proxy1.com", "http://proxy2.com"]
        )
        manager = AntiCrawlerManager(config)
        proxy = manager.get_random_proxy()
        assert proxy in ["http://proxy1.com", "http://proxy2.com"]

    def test_get_random_proxy_default(self):
        """测试使用默认代理"""
        config = AntiCrawlerConfig(default_proxy="http://127.0.0.1:7890")
        manager = AntiCrawlerManager(config)
        proxy = manager.get_random_proxy()
        assert proxy == "http://127.0.0.1:7890"

    def test_get_random_proxy_no_proxy(self):
        """测试无代理配置"""
        config = AntiCrawlerConfig()
        config.default_proxy = None
        config.proxy_pool = None
        manager = AntiCrawlerManager(config)
        proxy = manager.get_random_proxy()
        assert proxy is None

    def test_should_retry_timeout(self):
        """测试超时错误应该重试"""
        exception = Exception("timeout error")
        assert self.manager.should_retry(0, exception) is True
        assert self.manager.should_retry(1, exception) is True

    def test_should_retry_max_retries(self):
        """测试超过最大重试次数不重试"""
        exception = Exception("timeout error")
        assert self.manager.should_retry(3, exception) is False
        assert self.manager.should_retry(4, exception) is False

    def test_should_not_retry_other_error(self):
        """测试其他错误不重试"""
        exception = Exception("some other error")
        assert self.manager.should_retry(0, exception) is False


class TestBiliDataClient:
    """B站API客户端测试类"""

    def setup_method(self):
        """测试前置设置"""
        self.client = BiliDataClient()

    def test_parse_number_integer(self):
        """测试解析整数"""
        assert self.client._parse_number("12345") == 12345

    def test_parse_number_wan(self):
        """测试解析万单位"""
        assert self.client._parse_number("1.2万") == 12000

    def test_parse_number_yi(self):
        """测试解析亿单位"""
        assert self.client._parse_number("1.5亿") == 150000000

    def test_parse_number_empty(self):
        """测试解析空字符串"""
        assert self.client._parse_number("") == 0
        assert self.client._parse_number(None) == 0

    def test_video_search_result_creation(self):
        """测试VideoSearchResult创建"""
        result = VideoSearchResult(
            bvid="BV1234567890",
            title="测试视频",
            author="测试UP主",
            view_count=10000,
            like_count=1000,
            pubdate=1234567890,
        )
        assert result.bvid == "BV1234567890"
        assert result.title == "测试视频"
        assert result.view_count == 10000

    def test_video_detail_creation(self):
        """测试VideoDetail创建"""
        detail = VideoDetail(
            bvid="BV1234567890",
            title="测试视频",
            author="测试UP主",
            channel="娱乐",
            view_count=10000,
            like_count=1000,
            favorite_count=500,
            reply_count=100,
            pubdate=1234567890,
            cover_url="https://example.com/cover.jpg",
        )
        assert detail.channel == "娱乐"
        assert detail.favorite_count == 500

    def test_video_update_result_creation(self):
        """测试VideoUpdateResult创建"""
        result = VideoUpdateResult(
            bvid="BV1234567890",
            view_count=10000,
            like_count=1000,
            favorite_count=500,
            reply_count=100,
            success=True,
        )
        assert result.success is True
        assert result.error is None

    def test_video_update_result_failure(self):
        """测试VideoUpdateResult失败情况"""
        result = VideoUpdateResult(
            bvid="BV1234567890",
            view_count=0,
            like_count=0,
            favorite_count=0,
            reply_count=0,
            success=False,
            error="Failed to get video detail",
        )
        assert result.success is False
        assert result.error == "Failed to get video detail"


class TestVideoDiscoverer:
    """视频发现器测试类"""

    def setup_method(self):
        """测试前置设置"""
        self.discoverer = VideoDiscoverer(
            min_view_count=3000,
            min_like_count=100
        )

    def test_is_valid_video_pass(self):
        """测试有效视频过滤通过"""
        result = VideoSearchResult(
            bvid="BV1234567890",
            title="测试视频",
            author="测试UP主",
            view_count=5000,
            like_count=200,
            pubdate=1234567890,
        )
        assert self.discoverer._is_valid_video(result) is True

    def test_is_valid_video_low_view(self):
        """测试播放量过低被过滤"""
        result = VideoSearchResult(
            bvid="BV1234567890",
            title="测试视频",
            author="测试UP主",
            view_count=2000,  # 低于3000
            like_count=200,
            pubdate=1234567890,
        )
        assert self.discoverer._is_valid_video(result) is False

    def test_is_valid_video_low_like(self):
        """测试点赞量过低被过滤"""
        result = VideoSearchResult(
            bvid="BV1234567890",
            title="测试视频",
            author="测试UP主",
            view_count=5000,
            like_count=50,  # 低于100
            pubdate=1234567890,
        )
        assert self.discoverer._is_valid_video(result) is False

    def test_detail_to_video(self):
        """测试VideoDetail转换为Video"""
        detail = VideoDetail(
            bvid="BV1234567890",
            title="测试视频",
            author="测试UP主",
            channel="娱乐",
            view_count=10000,
            like_count=1000,
            favorite_count=500,
            reply_count=100,
            pubdate=1234567890,
            cover_url="https://example.com/cover.jpg",
        )

        video = self.discoverer._detail_to_video(detail, "测试关键词")

        assert video.bvid == "BV1234567890"
        assert video.title == "测试视频"
        assert video.channel == "娱乐"
        assert video.keyword == "测试关键词"
        assert video.view_today == 10000
        assert video.status == VideoStatus.MONITORING

    def test_filter_valid_videos(self):
        """测试过滤有效视频列表"""
        videos = [
            Video(bvid="BV1", view_today=5000, like_count=200),
            Video(bvid="BV2", view_today=2000, like_count=200),  # 播放量不足
            Video(bvid="BV3", view_today=5000, like_count=50),   # 点赞不足
            Video(bvid="BV4", view_today=10000, like_count=500),
        ]

        valid = self.discoverer.filter_valid_videos(videos)
        assert len(valid) == 2
        assert valid[0].bvid == "BV1"
        assert valid[1].bvid == "BV4"

    @patch("src.crawlers.video_discoverer.BiliDataClient")
    def test_discover_by_keyword(self, mock_client_class):
        """测试按关键词发现视频"""
        # 创建mock客户端
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # mock搜索结果
        mock_client.search_videos.return_value = [
            VideoSearchResult(
                bvid="BV1234567890",
                title="测试视频",
                author="测试UP主",
                view_count=5000,
                like_count=200,
                pubdate=1234567890,
            )
        ]

        # mock视频详情
        mock_client.get_video_detail.return_value = VideoDetail(
            bvid="BV1234567890",
            title="测试视频",
            author="测试UP主",
            channel="娱乐",
            view_count=5000,
            like_count=200,
            favorite_count=100,
            reply_count=50,
            pubdate=1234567890,
            cover_url="https://example.com/cover.jpg",
        )

        discoverer = VideoDiscoverer(client=mock_client)

        # mock monitor_service
        mock_monitor_service = MagicMock()
        mock_monitor_service.get_video_by_bvid.return_value = None
        discoverer.monitor_service = mock_monitor_service

        videos = discoverer.discover_by_keyword("测试", max_pages=1)

        assert len(videos) == 1
        assert videos[0].bvid == "BV1234567890"

    def test_save_discovered_videos(self):
        """测试保存发现的视频"""
        videos = [
            Video(bvid="BV1", title="视频1", channel="娱乐"),
            Video(bvid="BV2", title="视频2", channel="游戏"),
        ]

        # mock monitor_service
        mock_service = MagicMock()
        mock_service.get_video_by_bvid.return_value = None
        mock_service.add_video.return_value = videos[0]

        discoverer = VideoDiscoverer(monitor_service=mock_service)
        success, skip, error = discoverer.save_discovered_videos(videos)

        assert success == 2
        assert skip == 0
        assert error == 0

    def test_save_discovered_videos_skip_existing(self):
        """测试跳过已存在的视频"""
        videos = [
            Video(bvid="BV1", title="视频1", channel="娱乐"),
        ]

        mock_service = MagicMock()
        mock_service.get_video_by_bvid.return_value = Video(bvid="BV1")  # 已存在

        discoverer = VideoDiscoverer(monitor_service=mock_service)
        success, skip, error = discoverer.save_discovered_videos(videos, skip_existing=True)

        assert success == 0
        assert skip == 1
        assert error == 0


class TestVideoStatusTransition:
    """视频状态流转测试"""

    def test_video_status_enum_values(self):
        """测试视频状态枚举值"""
        assert VideoStatus.MONITORING.value == "monitoring"
        assert VideoStatus.FEATURED.value == "featured"
        assert VideoStatus.DECLINED.value == "declined"

    def test_video_default_status(self):
        """测试视频默认状态"""
        video = Video(bvid="BV1234567890")
        assert video.status == VideoStatus.MONITORING

    def test_video_status_transition(self):
        """测试视频状态流转"""
        video = Video(bvid="BV1234567890", status=VideoStatus.MONITORING)

        # monitoring -> featured
        video.status = VideoStatus.FEATURED
        assert video.status == VideoStatus.FEATURED

        # featured -> declined
        video.status = VideoStatus.DECLINED
        assert video.status == VideoStatus.DECLINED

        # declined -> monitoring (特殊情况可能需要)
        video.status = VideoStatus.MONITORING
        assert video.status == VideoStatus.MONITORING
