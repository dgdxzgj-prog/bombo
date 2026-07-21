"""
自适应判定与参数校准单元测试
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from src.models.video import Video, VideoStatus
from src.models.channel import ChannelConfig
from src.services.selectors import (
    BurstSelector,
    BaseVolumeSelector,
    ColdStartSelector,
    DeclineSelector,
)
from src.services.hot_judge import HotJudgeService
from src.services.param_calibrator import ParamCalibrator


class TestBurstSelector:
    """BurstSelector测试类"""

    def setup_method(self):
        """测试前置设置"""
        self.selector = BurstSelector()
        self.config = ChannelConfig(
            channel_id="entertainment",
            channel_name="娱乐",
            burst_growth_threshold=100.0,
            burst_volume_threshold=50000,
            is_locked=False,
        )

    def test_should_feature_pass(self):
        """测试满足爆发条件"""
        video = Video(
            bvid="BV1234567890",
            growth_rate=150.0,
            view_today=80000,
        )
        assert self.selector.should_feature(video, self.config) is True

    def test_should_feature_low_growth(self):
        """测试增速不足不通过"""
        video = Video(
            bvid="BV1234567890",
            growth_rate=50.0,  # 低于100%
            view_today=80000,
        )
        assert self.selector.should_feature(video, self.config) is False

    def test_should_feature_low_volume(self):
        """测试播放量不足不通过"""
        video = Video(
            bvid="BV1234567890",
            growth_rate=150.0,
            view_today=30000,  # 低于50000
        )
        assert self.selector.should_feature(video, self.config) is False

    def test_should_feature_both_fail(self):
        """测试增速和播放量都不足"""
        video = Video(
            bvid="BV1234567890",
            growth_rate=50.0,
            view_today=30000,
        )
        assert self.selector.should_feature(video, self.config) is False

    def test_should_feature_locked_config(self):
        """测试锁定配置且阈值为0时不通过"""
        config = ChannelConfig(
            channel_id="entertainment",
            is_locked=True,
            burst_growth_threshold=0,
        )
        video = Video(bvid="BV1234567890", growth_rate=200.0, view_today=100000)
        assert self.selector.should_feature(video, config) is False

    def test_get_burst_score(self):
        """测试爆发评分计算"""
        video = Video(
            bvid="BV1234567890",
            growth_rate=150.0,
            view_today=80000,
        )
        score = self.selector.get_burst_score(video, self.config)
        assert score > 0

    def test_get_burst_score_not_featured(self):
        """测试不满足条件时评分为0"""
        video = Video(
            bvid="BV1234567890",
            growth_rate=50.0,
            view_today=30000,
        )
        score = self.selector.get_burst_score(video, self.config)
        assert score == 0.0


class TestBaseVolumeSelector:
    """BaseVolumeSelector测试类"""

    def setup_method(self):
        """测试前置设置"""
        self.selector = BaseVolumeSelector()
        self.config = ChannelConfig(
            channel_id="entertainment",
            channel_name="娱乐",
            burst_growth_threshold=100.0,
            burst_volume_threshold=50000,
            base_growth_threshold=50.0,
            base_volume_threshold=100000,
            is_locked=False,
        )

    def test_should_feature_pass(self):
        """测试满足兜底条件"""
        video = Video(
            bvid="BV1234567890",
            growth_rate=70.0,  # 50 <= 70 < 100
            view_today=150000,  # >= 100000
        )
        assert self.selector.should_feature(video, self.config) is True

    def test_should_feature_growth_too_high(self):
        """测试增速太高不通过（应该在爆发层）"""
        video = Video(
            bvid="BV1234567890",
            growth_rate=120.0,  # >= 100
            view_today=150000,
        )
        assert self.selector.should_feature(video, self.config) is False

    def test_should_feature_growth_too_low(self):
        """测试增速太低不通过"""
        video = Video(
            bvid="BV1234567890",
            growth_rate=30.0,  # < 50
            view_today=150000,
        )
        assert self.selector.should_feature(video, self.config) is False

    def test_should_feature_low_volume(self):
        """测试播放量不足不通过"""
        video = Video(
            bvid="BV1234567890",
            growth_rate=70.0,
            view_today=50000,  # < 100000
        )
        assert self.selector.should_feature(video, self.config) is False


class TestColdStartSelector:
    """ColdStartSelector测试类"""

    def setup_method(self):
        """测试前置设置"""
        self.selector = ColdStartSelector()
        self.config = ChannelConfig(
            channel_id="entertainment",
            channel_name="娱乐",
            cold_start_threshold=10000,
            cold_start_hours=72,
            is_locked=False,
        )

    def test_should_feature_pass(self):
        """测试满足冷启动条件"""
        video = Video(
            bvid="BV1234567890",
            pubdate=datetime.now() - timedelta(hours=24),  # 24小时前发布
            view_today=20000,  # >= 10000
        )
        assert self.selector.should_feature(video, self.config) is True

    def test_should_feature_too_old(self):
        """测试发布太久不通过"""
        video = Video(
            bvid="BV1234567890",
            pubdate=datetime.now() - timedelta(hours=100),  # 超过72小时
            view_today=20000,
        )
        assert self.selector.should_feature(video, self.config) is False

    def test_should_feature_low_volume(self):
        """测试播放量不足不通过"""
        video = Video(
            bvid="BV1234567890",
            pubdate=datetime.now() - timedelta(hours=24),
            view_today=5000,  # < 10000
        )
        assert self.selector.should_feature(video, self.config) is False

    def test_should_feature_no_pubdate(self):
        """测试无发布时间不通过"""
        video = Video(bvid="BV1234567890", pubdate=None, view_today=20000)
        assert self.selector.should_feature(video, self.config) is False


class TestDeclineSelector:
    """DeclineSelector测试类"""

    def setup_method(self):
        """测试前置设置"""
        self.selector = DeclineSelector()
        self.config = ChannelConfig(
            channel_id="entertainment",
            decline_growth_threshold=10.0,
            is_locked=False,
        )

    def test_should_decline_pass(self):
        """测试应该衰退"""
        video = Video(bvid="BV1234567890", growth_rate=5.0)  # < 10
        assert self.selector.should_decline(video, self.config) is True

    def test_should_decline_fail(self):
        """测试不应该衰退"""
        video = Video(bvid="BV1234567890", growth_rate=15.0)  # >= 10
        assert self.selector.should_decline(video, self.config) is False

    def test_should_decline_locked_config(self):
        """测试锁定配置且阈值为0时不衰退"""
        config = ChannelConfig(
            channel_id="entertainment",
            is_locked=True,
            decline_growth_threshold=0,
        )
        video = Video(bvid="BV1234567890", growth_rate=5.0)
        assert self.selector.should_decline(video, config) is False


class TestHotJudgeService:
    """HotJudgeService测试类"""

    def setup_method(self):
        """测试前置设置"""
        self.mock_monitor_service = MagicMock()
        self.mock_channel_service = MagicMock()
        self.service = HotJudgeService(
            monitor_service=self.mock_monitor_service,
            channel_service=self.mock_channel_service,
        )

    def test_is_hot_video_burst(self):
        """测试爆发层判定"""
        video = Video(
            bvid="BV1234567890",
            channel="entertainment",
            growth_rate=150.0,
            view_today=80000,
        )
        config = ChannelConfig(
            channel_id="entertainment",
            burst_growth_threshold=100.0,
            burst_volume_threshold=50000,
        )

        self.mock_monitor_service.get_video_by_bvid.return_value = video
        self.mock_channel_service.get_channel_by_id.return_value = config

        is_hot, reason = self.service.is_hot_video("BV1234567890")

        assert is_hot is True
        assert "Burst" in reason

    def test_is_hot_video_base(self):
        """测试兜底层判定"""
        video = Video(
            bvid="BV1234567890",
            channel="entertainment",
            growth_rate=70.0,
            view_today=150000,
        )
        config = ChannelConfig(
            channel_id="entertainment",
            burst_growth_threshold=100.0,
            burst_volume_threshold=50000,
            base_growth_threshold=50.0,
            base_volume_threshold=100000,
        )

        self.mock_monitor_service.get_video_by_bvid.return_value = video
        self.mock_channel_service.get_channel_by_id.return_value = config

        is_hot, reason = self.service.is_hot_video("BV1234567890")

        assert is_hot is True
        assert "Base" in reason

    def test_is_hot_video_cold(self):
        """测试冷启动判定"""
        video = Video(
            bvid="BV1234567890",
            channel="entertainment",
            pubdate=datetime.now() - timedelta(hours=24),
            view_today=20000,
            growth_rate=0.0,  # 确保不满足爆发层和兜底层条件
        )
        config = ChannelConfig(
            channel_id="entertainment",
            burst_growth_threshold=100.0,
            burst_volume_threshold=50000,
            base_growth_threshold=50.0,   # 兜底阈值设高，防止误匹配
            base_volume_threshold=100000, # 兜底播放量设高，防止误匹配
            cold_start_threshold=10000,
            cold_start_hours=72,
        )

        self.mock_monitor_service.get_video_by_bvid.return_value = video
        self.mock_channel_service.get_channel_by_id.return_value = config

        is_hot, reason = self.service.is_hot_video("BV1234567890")

        assert is_hot is True
        assert "Cold" in reason

    def test_is_hot_video_not_hot(self):
        """测试不是爆款"""
        video = Video(
            bvid="BV1234567890",
            channel="entertainment",
            growth_rate=30.0,
            view_today=30000,
        )
        config = ChannelConfig(
            channel_id="entertainment",
            burst_growth_threshold=100.0,
            burst_volume_threshold=50000,
            base_growth_threshold=50.0,
            base_volume_threshold=100000,
            cold_start_threshold=10000,
            cold_start_hours=72,
        )

        self.mock_monitor_service.get_video_by_bvid.return_value = video
        self.mock_channel_service.get_channel_by_id.return_value = config

        is_hot, reason = self.service.is_hot_video("BV1234567890")

        assert is_hot is False
        assert "Not hot" in reason

    def test_is_hot_video_not_found(self):
        """测试视频不存在"""
        self.mock_monitor_service.get_video_by_bvid.return_value = None

        is_hot, reason = self.service.is_hot_video("BV0000000000")

        assert is_hot is False
        assert "not found" in reason


class TestParamCalibrator:
    """ParamCalibrator测试类"""

    def setup_method(self):
        """测试前置设置"""
        self.mock_channel_service = MagicMock()
        self.mock_monitor_service = MagicMock()
        self.calibrator = ParamCalibrator(
            channel_service=self.mock_channel_service,
            monitor_service=self.mock_monitor_service,
        )

    def test_calculate_percentile(self):
        """测试分位值计算"""
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

        # P90 应该是 90左右
        p90 = self.calibrator._calculate_percentile(values, 90)
        assert 85 <= p90 <= 95

        # P50 应该是 50左右
        p50 = self.calibrator._calculate_percentile(values, 50)
        assert 45 <= p50 <= 55

    def test_calculate_percentile_empty(self):
        """测试空列表"""
        result = self.calibrator._calculate_percentile([], 50)
        assert result == 0.0

    def test_clamp_burst_growth(self):
        """测试爆发增速边界校验"""
        # 低于最小值
        assert self.calibrator._clamp_burst_growth(30.0) == 50.0

        # 高于最大值
        assert self.calibrator._clamp_burst_growth(250.0) == 200.0

        # 正常值
        assert self.calibrator._clamp_burst_growth(100.0) == 100.0

    def test_calibrate_channel_insufficient_samples(self):
        """测试样本不足时使用默认值"""
        self.mock_channel_service.get_channel_by_id.return_value = ChannelConfig(
            channel_id="entertainment",
            is_locked=False,
        )
        # 返回少于7个视频
        self.mock_monitor_service.get_videos_by_channel.return_value = [
            Video(bvid="BV1"),
            Video(bvid="BV2"),
            Video(bvid="BV3"),
        ]
        # 样本不足时调用 update_channel_params
        self.mock_channel_service.update_channel_params.return_value = True

        result = self.calibrator.calibrate_channel("entertainment")

        assert result is True
        self.mock_channel_service.update_channel_params.assert_called_once()

    def test_calibrate_all_channels(self):
        """测试批量校准"""
        self.mock_channel_service.get_unlocked_channels.return_value = [
            ChannelConfig(channel_id="entertainment"),
            ChannelConfig(channel_id="gaming"),
        ]
        self.mock_monitor_service.get_videos_by_channel.return_value = []
        self.mock_channel_service.get_channel_by_id.return_value = ChannelConfig(
            channel_id="test",
            is_locked=False,
        )

        result = self.calibrator.calibrate_all_channels()

        assert result["total"] == 2
        assert "calibrated_at" in result

    def test_get_calibration_preview_sufficient(self):
        """测试校准预览-样本充足"""
        videos = [
            Video(bvid="BV1", growth_rate=100.0, view_today=50000, status=VideoStatus.FEATURED),
            Video(bvid="BV2", growth_rate=80.0, view_today=40000, status=VideoStatus.FEATURED),
            Video(bvid="BV3", growth_rate=60.0, view_today=30000, status=VideoStatus.MONITORING),
            Video(bvid="BV4", growth_rate=40.0, view_today=20000, status=VideoStatus.MONITORING),
            Video(bvid="BV5", growth_rate=20.0, view_today=10000, status=VideoStatus.MONITORING),
            Video(bvid="BV6", growth_rate=10.0, view_today=5000, status=VideoStatus.MONITORING),
            Video(bvid="BV7", growth_rate=5.0, view_today=3000, status=VideoStatus.MONITORING),
            Video(bvid="BV8", growth_rate=2.0, view_today=1000, status=VideoStatus.MONITORING),
        ]
        self.mock_monitor_service.get_videos_by_channel.return_value = videos

        preview = self.calibrator.get_calibration_preview("entertainment")

        assert preview["sufficient"] is True
        assert preview["sample_size"] == 8
        assert "suggested_params" in preview

    def test_get_calibration_preview_insufficient(self):
        """测试校准预览-样本不足"""
        self.mock_monitor_service.get_videos_by_channel.return_value = [
            Video(bvid="BV1"),
            Video(bvid="BV2"),
        ]

        preview = self.calibrator.get_calibration_preview("entertainment")

        assert preview["sufficient"] is False
        assert "message" in preview
