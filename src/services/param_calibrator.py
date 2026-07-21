"""
自适应参数校准器
每周自动计算各赛道判定阈值与评分权重
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import statistics

from src.models.channel import ChannelConfig
from src.models.video import Video, VideoStatus
from src.services.channel_config_service import ChannelConfigService
from src.services.monitor_pool_service import MonitorPoolService


class ParamCalibrator:
    """
    自适应参数校准器

    基于过去14天的历史数据，自动计算各赛道、各生命周期桶的判定阈值
    包括：爆发增速阈值、播放量基线、兜底阈值、冷启动阈值、衰退阈值
    """

    # 校准使用的历史数据天数
    HISTORY_DAYS = 14

    # 爆发层参数分位值
    BURST_GROWTH_PERCENTILE = 90
    BURST_VOLUME_PERCENTILE = 80  # 历史上榜视频平均播放量的80%

    # 兜底层参数分位值
    BASE_GROWTH_PERCENTILE = 50
    BASE_VOLUME_PERCENTILE = 60  # 历史上榜视频最高播放量的60%

    # 冷启动参数分位值
    COLD_START_PERCENTILE = 85

    # 衰退参数分位值
    DECLINE_PERCENTILE = 30

    # 边界限制
    BURST_GROWTH_MIN = 50.0    # 最低50%
    BURST_GROWTH_MAX = 200.0   # 最高200%
    COLD_START_HOURS_DEFAULT = 72  # 冷启动时间窗口默认72小时

    def __init__(
        self,
        channel_service: Optional[ChannelConfigService] = None,
        monitor_service: Optional[MonitorPoolService] = None
    ):
        self.channel_service = channel_service or ChannelConfigService()
        self.monitor_service = monitor_service or MonitorPoolService()

    def calibrate_all_channels(self) -> dict:
        """
        校准所有赛道参数

        Returns:
            校准结果统计
        """
        channels = self.channel_service.get_unlocked_channels()
        total = len(channels)
        success = 0
        failed = 0
        errors = []

        for channel in channels:
            try:
                result = self.calibrate_channel(channel.channel_id)
                if result:
                    success += 1
                else:
                    failed += 1
                    errors.append(f"{channel.channel_id}: calibration failed")
            except Exception as e:
                failed += 1
                errors.append(f"{channel.channel_id}: {str(e)}")

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "errors": errors,
            "calibrated_at": datetime.now().isoformat(),
        }

    def calibrate_channel(self, channel_id: str) -> bool:
        """
        校准单个赛道参数

        Args:
            channel_id: 赛道ID

        Returns:
            是否成功
        """
        # 获取赛道配置
        config = self.channel_service.get_channel_by_id(channel_id)
        if not config:
            return False

        # 获取该赛道过去14天的监控数据
        videos = self._get_channel_history_videos(channel_id)

        if len(videos) < 7:
            # 样本量不足，使用全局默认值
            return self._apply_cold_start_params(channel_id)

        # 计算各参数
        growth_rates = [v.growth_rate for v in videos if v.growth_rate > 0]
        view_counts = [v.view_today for v in videos if v.view_today > 0]

        if not growth_rates or not view_counts:
            return False

        # 计算各分位值
        burst_growth = self._calculate_percentile(growth_rates, self.BURST_GROWTH_PERCENTILE)
        burst_volume = self._calculate_percentile(view_counts, self.BURST_VOLUME_PERCENTILE)
        base_growth = self._calculate_percentile(growth_rates, self.BASE_GROWTH_PERCENTILE)
        base_volume = self._calculate_percentile(view_counts, self.BASE_VOLUME_PERCENTILE)
        cold_start_threshold = self._calculate_percentile(view_counts, self.COLD_START_PERCENTILE)
        decline_threshold = self._calculate_percentile(growth_rates, self.DECLINE_PERCENTILE)

        # 边界校验
        burst_growth = self._clamp_burst_growth(burst_growth)

        # 获取有效样本量（已上榜视频数量）
        featured_count = len([v for v in videos if v.status == VideoStatus.FEATURED])

        # 更新参数
        return self.channel_service.update_calibration_result(
            channel_id=channel_id,
            burst_growth_threshold=burst_growth,
            burst_volume_threshold=burst_volume,
            base_growth_threshold=base_growth,
            base_volume_threshold=base_volume,
            cold_start_threshold=cold_start_threshold,
            decline_growth_threshold=decline_threshold,
            sample_size=featured_count,
        )

    def _get_channel_history_videos(self, channel_id: str) -> List[Video]:
        """
        获取赛道历史视频数据

        实际应从数据库查询过去14天的数据
        这里简化处理，查询该赛道所有监控中的视频
        """
        return self.monitor_service.get_videos_by_channel(channel_id, limit=10000)

    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """
        计算分位值

        Args:
            values: 数值列表
            percentile: 分位值(0-100)

        Returns:
            分位数值
        """
        if not values:
            return 0.0

        sorted_values = sorted(values)
        index = (len(sorted_values) - 1) * percentile / 100
        lower = int(index)
        upper = lower + 1

        if upper >= len(sorted_values):
            return sorted_values[-1]

        weight = index - lower
        return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight

    def _clamp_burst_growth(self, value: float) -> float:
        """
        边界校验：爆发增速阈值限制在[50%, 200%]
        """
        return max(self.BURST_GROWTH_MIN, min(self.BURST_GROWTH_MAX, value))

    def _apply_cold_start_params(self, channel_id: str) -> bool:
        """
        应用冷启动参数（样本不足时使用全局默认值）
        """
        # 全局默认冷启动参数
        default_cold_start = 5000   # 默认冷启动播放量阈值
        default_decline = 10.0      # 默认衰退阈值10%

        return self.channel_service.update_channel_params(
            channel_id=channel_id,
            cold_start_threshold=default_cold_start,
            decline_growth_threshold=default_decline,
        )

    def get_calibration_preview(self, channel_id: str) -> Dict[str, Any]:
        """
        获取校准预览（不实际更新，只计算预期值）

        Returns:
            预览数据
        """
        videos = self._get_channel_history_videos(channel_id)

        if len(videos) < 7:
            return {
                "channel_id": channel_id,
                "sample_size": len(videos),
                "sufficient": False,
                "message": "样本量不足，使用全局默认值",
                "suggested_params": {
                    "cold_start_threshold": 5000,
                    "decline_growth_threshold": 10.0,
                }
            }

        growth_rates = [v.growth_rate for v in videos if v.growth_rate > 0]
        view_counts = [v.view_today for v in videos if v.view_today > 0]
        featured_count = len([v for v in videos if v.status == VideoStatus.FEATURED])

        return {
            "channel_id": channel_id,
            "sample_size": len(videos),
            "featured_count": featured_count,
            "sufficient": True,
            "suggested_params": {
                "burst_growth_threshold": self._clamp_burst_growth(
                    self._calculate_percentile(growth_rates, self.BURST_GROWTH_PERCENTILE)
                ),
                "burst_volume_threshold": int(self._calculate_percentile(view_counts, self.BURST_VOLUME_PERCENTILE)),
                "base_growth_threshold": self._calculate_percentile(growth_rates, self.BASE_GROWTH_PERCENTILE),
                "base_volume_threshold": int(self._calculate_percentile(view_counts, self.BASE_VOLUME_PERCENTILE)),
                "cold_start_threshold": int(self._calculate_percentile(view_counts, self.COLD_START_PERCENTILE)),
                "decline_growth_threshold": self._calculate_percentile(growth_rates, self.DECLINE_PERCENTILE),
            }
        }

    def calibrate_with_lock_check(self, channel_id: str) -> dict:
        """
        带锁定检查的校准
        如果赛道已锁定，跳过校准
        """
        config = self.channel_service.get_channel_by_id(channel_id)
        if not config:
            return {"success": False, "error": "Channel not found"}

        if config.is_locked:
            return {
                "success": False,
                "error": "Channel is locked, calibration skipped",
                "channel_id": channel_id,
            }

        success = self.calibrate_channel(channel_id)
        return {
            "success": success,
            "channel_id": channel_id,
            "calibrated_at": datetime.now().isoformat(),
        }
