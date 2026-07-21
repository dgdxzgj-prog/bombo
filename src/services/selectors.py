"""
自适应多信号综合判定模块
实现三层筛选逻辑：
1. BurstSelector - 增速爆发筛选
2. BaseSelector - 体量兜底筛选
3. ColdStartSelector - 冷启动筛选
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from src.models.video import Video, VideoStatus
from src.models.channel import ChannelConfig


class BaseSelector(ABC):
    """筛选器基类"""

    @abstractmethod
    def should_feature(self, video: Video, config: ChannelConfig) -> bool:
        """判断视频是否应该上榜"""
        pass


class BurstSelector(BaseSelector):
    """
    第一层：增速爆发筛选
    条件: 增速 >= 赛道P90阈值 AND 播放量 >= 赛道基线阈值
    目标: 捕捉正在被平台快速推送的新锐爆款
    """

    def should_feature(self, video: Video, config: ChannelConfig) -> bool:
        """判断是否满足爆发条件"""
        if config.is_locked and config.burst_growth_threshold <= 0:
            return False

        growth_condition = video.growth_rate >= config.burst_growth_threshold
        volume_condition = video.view_today >= config.burst_volume_threshold

        return growth_condition and volume_condition

    def get_burst_score(self, video: Video, config: ChannelConfig) -> float:
        """
        计算爆发评分
        用于综合排序
        """
        if not self.should_feature(video, config):
            return 0.0

        # 评分公式: 增速得分 * 0.6 + 体量得分 * 0.4
        growth_score = min(video.growth_rate / config.burst_growth_threshold, 2.0) * 0.6 if config.burst_growth_threshold > 0 else 0
        volume_score = min(video.view_today / config.burst_volume_threshold, 2.0) * 0.4 if config.burst_volume_threshold > 0 else 0

        return growth_score + volume_score


class BaseVolumeSelector(BaseSelector):
    """
    第二层：体量兜底筛选
    条件: 兜底阈值 <= 增速 < 爆发阈值 AND 播放量 >= 兜底阈值
    目标: 捕获播放基数大、增速放缓但依旧具备高热度价值的长期爆款
    """

    def should_feature(self, video: Video, config: ChannelConfig) -> bool:
        """判断是否满足兜底条件"""
        if config.is_locked and config.base_growth_threshold <= 0:
            return False

        # 增速在兜底阈值和爆发阈值之间
        growth_in_range = (
            config.base_growth_threshold <= video.growth_rate < config.burst_growth_threshold
        )

        # 播放量达到兜底阈值
        volume_condition = video.view_today >= config.base_volume_threshold

        return growth_in_range and volume_condition

    def get_base_score(self, video: Video, config: ChannelConfig) -> float:
        """
        计算兜底评分
        """
        if not self.should_feature(video, config):
            return 0.0

        # 评分公式: 体量得分 * 0.7 + 增速得分 * 0.3
        volume_score = min(video.view_today / config.base_volume_threshold, 2.0) * 0.7 if config.base_volume_threshold > 0 else 0
        growth_ratio = video.growth_rate / config.burst_growth_threshold if config.burst_growth_threshold > 0 else 0
        growth_score = growth_ratio * 0.3

        return volume_score + growth_score


class ColdStartSelector(BaseSelector):
    """
    第三层：冷启动专项筛选
    条件: 发布<72小时 AND 播放量 >= 冷启动阈值
    目标: 针对发布初期的新视频专项识别潜力爆款
    """

    def should_feature(self, video: Video, config: ChannelConfig) -> bool:
        """判断是否满足冷启动条件"""
        if video.pubdate is None:
            return False

        # 计算发布时长
        hours_since_pub = (datetime.now() - video.pubdate).total_seconds() / 3600

        if hours_since_pub >= config.cold_start_hours:
            return False

        # 播放量达到冷启动阈值
        return video.view_today >= config.cold_start_threshold

    def get_cold_start_score(self, video: Video, config: ChannelConfig) -> float:
        """
        计算冷启动评分
        """
        if not self.should_feature(video, config):
            return 0.0

        hours_since_pub = (datetime.now() - video.pubdate).total_seconds() / 3600
        time_factor = 1.0 - (hours_since_pub / config.cold_start_hours)
        volume_score = min(video.view_today / config.cold_start_threshold, 2.0) if config.cold_start_threshold > 0 else 0

        return time_factor * 0.4 + volume_score * 0.6


class DeclineSelector:
    """
    衰退筛选器
    条件: 连续7日增速 < 赛道衰退阈值(P30)
    目标: 识别热度下滑的视频，移出常规监控队列
    """

    def should_decline(self, video: Video, config: ChannelConfig) -> bool:
        """判断视频是否应该衰退"""
        if config.is_locked and config.decline_growth_threshold <= 0:
            return False

        return video.growth_rate < config.decline_growth_threshold

    def get_decline_days(self, video: Video, config: ChannelConfig, consecutive_days: int) -> int:
        """
        计算连续衰退天数
        实际应从数据库读取历史数据
        这里简化处理
        """
        if self.should_decline(video, config):
            return consecutive_days
        return 0
