"""
爆款综合判定服务
整合三层筛选逻辑进行综合判定
"""
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

from src.models.video import Video, VideoStatus
from src.models.channel import ChannelConfig
from src.services.selectors import (
    BurstSelector,
    BaseVolumeSelector,
    ColdStartSelector,
    DeclineSelector,
)
from src.services.monitor_pool_service import MonitorPoolService
from src.services.channel_config_service import ChannelConfigService
from src.services.snapshot_service import SnapshotService


# 视频成熟门槛（小时）
MATURITY_THRESHOLD_HOURS = 24


class HotJudgeService:
    """爆款综合判定服务"""

    def __init__(
        self,
        monitor_service: Optional[MonitorPoolService] = None,
        channel_service: Optional[ChannelConfigService] = None,
        snapshot_service: Optional[SnapshotService] = None,
    ):
        self.monitor_service = monitor_service or MonitorPoolService()
        self.channel_service = channel_service or ChannelConfigService()
        self.snapshot_service = snapshot_service or SnapshotService()

        # 初始化各层筛选器
        self.burst_selector = BurstSelector()
        self.base_selector = BaseVolumeSelector()
        self.cold_start_selector = ColdStartSelector()
        self.decline_selector = DeclineSelector()

    def is_mature_video(self, bvid: str, current_time: Optional[datetime] = None) -> Tuple[bool, float]:
        """
        判断视频是否已成熟（入库满24小时）

        Args:
            bvid: 视频bvid
            current_time: 当前时间，默认now

        Returns:
            (is_mature, age_hours): 是否成熟及入库时长
        """
        if current_time is None:
            current_time = datetime.now()

        video = self.monitor_service.get_video_by_bvid(bvid)
        if not video or not video.first_seen:
            return False, 0.0

        age_hours = (current_time - video.first_seen).total_seconds() / 3600
        is_mature = age_hours >= MATURITY_THRESHOLD_HOURS

        return is_mature, age_hours

    def calculate_sliding_growth_rate(self, bvid: str, current_view_count: int, current_time: Optional[datetime] = None) -> Tuple[float, bool]:
        """
        计算滑动窗口真实增速

        Args:
            bvid: 视频bvid
            current_view_count: 当前播放量
            current_time: 当前时间，默认now

        Returns:
            (growth_rate, has_complete_window): 增速和是否有完整窗口
        """
        if current_time is None:
            current_time = datetime.now()

        return self.snapshot_service.calculate_sliding_growth_rate(
            bvid=bvid,
            current_view_count=current_view_count,
            current_time=current_time,
            window_hours=MATURITY_THRESHOLD_HOURS,
        )

    def calculate_sliding_growth_rate_detail(self, bvid: str, current_view_count: int, current_time: Optional[datetime] = None) -> Tuple[float, bool, int]:
        """
        计算滑动窗口真实增速（详细版）

        Args:
            bvid: 视频bvid
            current_view_count: 当前播放量
            current_time: 当前时间，默认now

        Returns:
            (growth_rate, has_complete_window, view_24h_ago): 增速、是否有完整窗口、24h前播放量
        """
        if current_time is None:
            current_time = datetime.now()

        return self.snapshot_service.calculate_sliding_growth_rate_detail(
            bvid=bvid,
            current_view_count=current_view_count,
            current_time=current_time,
            window_hours=MATURITY_THRESHOLD_HOURS,
        )

    def is_hot_video(self, bvid: str, current_view_count: Optional[int] = None) -> Tuple[bool, str]:
        """
        判断视频是否爆款（统一三层判定条件）

        Rules:
        - 入库未满24小时的视频不参与爆款判定
        - 入库>=24小时的视频使用滑动窗口真实增速
        - 滑动窗口数据不足时，无法判定（返回False）

        三层判定条件（统一标准）：
        1. 新锐爆发款：真实增速 ≥5% 且 24h窗口新增播放 ≥10万
        2. 高体量长期款：1% ≤ 真实增速 <5% 且 24h窗口新增播放 ≥50万
        3. 冷启动成熟款（发布<72小时）：24h窗口新增播放 ≥5万

        Args:
            bvid: 视频bvid
            current_view_count: 当前播放量（可选，如果不传则从数据库获取最新）

        Returns:
            (is_hot, reason): 是否爆款及判定原因
        """
        # 获取视频
        video = self.monitor_service.get_video_by_bvid(bvid)
        if not video:
            return False, "Video not found"

        # 检查视频是否成熟（入库满24小时）
        is_mature, age_hours = self.is_mature_video(bvid)
        if not is_mature:
            return False, f"Cold: Video not yet {MATURITY_THRESHOLD_HOURS}h old (age: {age_hours:.1f}h)"

        # 如果没有传入当前播放量，从数据库获取
        if current_view_count is None:
            current_view_count = video.view_today if video.view_today > 0 else video.view_yesterday

        # 计算滑动窗口增速和新增播放
        growth_rate, has_window, view_24h_ago = self.calculate_sliding_growth_rate_detail(bvid, current_view_count)

        # 如果没有完整的滑动窗口数据，无法判定
        if not has_window or view_24h_ago == 0:
            return False, f"No window: 缺少24h窗口数据，无法判定"

        # 计算24h窗口新增播放
        view_increment = current_view_count - view_24h_ago

        # 持久化增速到数据库
        self.monitor_service.update_video_growth_rate(bvid, growth_rate)

        # 统一三层判定条件
        # 条件1：新锐爆发款
        if growth_rate >= 5.0 and view_increment >= 100000:
            return True, f"Burst: 增速{growth_rate:.1f}%, 新增{view_increment/10000:.0f}万播放"

        # 条件2：高体量长期款
        if 1.0 <= growth_rate < 5.0 and view_increment >= 500000:
            return True, f"Base: 增速{growth_rate:.1f}%, 新增{view_increment/10000:.0f}万播放"

        # 条件3：冷启动成熟款（发布<72小时）
        if video.pubdate:
            publish_hours = (datetime.now() - video.pubdate).total_seconds() / 3600
            if publish_hours < 72 and view_increment >= 50000:
                return True, f"Cold: 发布{publish_hours:.0f}h, 新增{view_increment/10000:.0f}万播放"

        return False, f"Not hot: 增速{growth_rate:.1f}%, 新增{view_increment/10000:.0f}万播放"

    def judge_video(self, bvid: str, current_view_count: Optional[int] = None) -> bool:
        """
        判定并更新视频状态

        Args:
            bvid: 视频bvid
            current_view_count: 当前播放量（可选）

        Returns:
            是否被标记为爆款
        """
        is_hot, reason = self.is_hot_video(bvid, current_view_count)

        if is_hot:
            self.monitor_service.update_video_status(bvid, VideoStatus.FEATURED)

        return is_hot

    def judge_all_videos(self, channel: Optional[str] = None, mature_only: bool = True) -> dict:
        """
        批量判定视频是否爆款（流式处理，避免内存超限）

        Args:
            channel: 可选，限定赛道
            mature_only: 是否只判定成熟视频（默认True）

        Returns:
            判定结果统计
        """
        featured_count = 0
        skipped_count = 0
        errors = []

        if channel:
            # 对于指定赛道，仍使用原有方法（数据量较小）
            videos = self.monitor_service.get_videos_by_channel(channel)
            total = len(videos)
            video_iter = iter(videos)
        else:
            # 使用流式迭代器，先获取总数
            total = self.monitor_service.count_monitoring_videos()
            video_iter = self.monitor_service.iter_all_monitoring_videos(batch_size=500)

        for video in video_iter:
            try:
                # 检查是否成熟
                if mature_only:
                    is_mature, _ = self.is_mature_video(video.bvid)
                    if not is_mature:
                        skipped_count += 1
                        continue

                is_hot, _ = self.is_hot_video(video.bvid)
                if is_hot:
                    self.monitor_service.update_video_status(video.bvid, VideoStatus.FEATURED)
                    featured_count += 1
            except Exception as e:
                errors.append(f"{video.bvid}: {str(e)}")

        return {
            "total": total,
            "featured": featured_count,
            "skipped": skipped_count,
            "not_featured": total - featured_count - skipped_count,
            "errors": errors,
            "judged_at": datetime.now().isoformat(),
        }

    def should_decline_video(self, bvid: str, consecutive_days: int = 7) -> bool:
        """
        判断视频是否应该衰退
        """
        video = self.monitor_service.get_video_by_bvid(bvid)
        if not video:
            return False

        config = self._get_config_for_video(video)
        if not config:
            return False

        return self.decline_selector.should_decline(video, config)

    def cleanup_declined_videos(self, consecutive_days: int = 7) -> dict:
        """
        清理衰退视频（流式处理，避免内存超限）
        """
        total = self.monitor_service.count_monitoring_videos()
        declined_count = 0
        errors = []

        for video in self.monitor_service.iter_all_monitoring_videos(batch_size=500):
            try:
                if self.decline_selector.should_decline(video, self._get_config_for_video(video)):
                    self.monitor_service.update_video_status(video.bvid, VideoStatus.DECLINED)
                    declined_count += 1
            except Exception as e:
                errors.append(f"{video.bvid}: {str(e)}")

        return {
            "total_checked": total,
            "declined": declined_count,
            "errors": errors,
            "cleaned_at": datetime.now().isoformat(),
        }

    def _get_config_for_video(self, video: Video) -> ChannelConfig:
        """获取视频对应的赛道配置，如果不存在则返回默认配置"""
        config = self.channel_service.get_channel_by_id(video.channel)
        if not config:
            # 创建默认配置，使用视频的channel作为channel_name
            return ChannelConfig(
                channel_id=video.channel if video.channel else "unknown",
                channel_name=video.channel if video.channel else "未知",
            )
        return config

    def get_hot_score(self, bvid: str) -> Optional[float]:
        """
        获取视频爆款评分
        """
        video = self.monitor_service.get_video_by_bvid(bvid)
        if not video:
            return None

        config = self._get_config_for_video(video)
        if not config:
            return None

        burst_score = self.burst_selector.get_burst_score(video, config)
        base_score = self.base_selector.get_base_score(video, config)
        cold_score = self.cold_start_selector.get_cold_start_score(video, config)

        return max(burst_score, base_score, cold_score)

    def get_featured_videos(self, channel: Optional[str] = None, limit: int = 100) -> List[Video]:
        """
        获取已上榜的爆款视频列表
        """
        if channel:
            videos = self.monitor_service.get_videos_by_channel(channel, limit=limit * 2)
        else:
            videos = self.monitor_service.list_videos(status=VideoStatus.FEATURED, limit=limit * 2)

        scored_videos = []
        for video in videos:
            score = self.get_hot_score(video.bvid)
            if score and score > 0:
                scored_videos.append((video, score))

        scored_videos.sort(key=lambda x: x[1], reverse=True)
        return [v[0] for v in scored_videos[:limit]]
