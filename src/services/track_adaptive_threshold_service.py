"""
赛道自适应爆款判定服务
使用历史同赛道所有视频峰值在线分布分位数生成阈值
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import numpy as np

from sqlalchemy import text
from src.utils.database import get_db_session
from src.models.video import VideoStatus


class TrackAdaptiveThresholdService:
    """赛道自适应阈值计算服务"""

    def __init__(self):
        pass

    def get_track_config(self, channel_id: str) -> Optional[Dict]:
        """
        获取赛道配置

        Args:
            channel_id: 赛道ID

        Returns:
            赛道配置字典
        """
        with get_db_session() as session:
            result = session.execute(
                text("""
                    SELECT channel_id, channel_name, p_up, p_down, hysteresis_ratio,
                           window_days, min_sample_count, t_up, t_down,
                           t_up_min, t_down_min, last_threshold_update, threshold_sample_count
                    FROM channel_config
                    WHERE channel_id = :channel_id
                """),
                {"channel_id": channel_id}
            ).fetchone()

            if not result:
                return None

            return {
                "channel_id": result[0],
                "channel_name": result[1],
                "p_up": float(result[2]) if result[2] else 0.90,
                "p_down": float(result[3]) if result[3] else 0.70,
                "hysteresis_ratio": float(result[4]) if result[4] else 0.75,
                "window_days": result[5] if result[5] else 14,
                "min_sample_count": result[6] if result[6] else 30,
                "t_up": result[7] if result[7] else 0,
                "t_down": result[8] if result[8] else 0,
                "t_up_min": result[9] if result[9] else 100,
                "t_down_min": result[10] if result[10] else 50,
                "last_threshold_update": result[11],
                "threshold_sample_count": result[12] if result[12] else 0,
            }

    def get_all_active_tracks(self) -> List[Dict]:
        """
        获取所有活跃赛道

        Returns:
            赛道配置列表
        """
        with get_db_session() as session:
            results = session.execute(
                text("""
                    SELECT channel_id, channel_name, p_up, p_down, hysteresis_ratio,
                           window_days, min_sample_count, t_up, t_down,
                           t_up_min, t_down_min, last_threshold_update, threshold_sample_count
                    FROM channel_config
                    WHERE status = 'active'
                    ORDER BY sort_order
                """)
            ).fetchall()

            return [
                {
                    "channel_id": row[0],
                    "channel_name": row[1],
                    "p_up": float(row[2]) if row[2] else 0.90,
                    "p_down": float(row[3]) if row[3] else 0.70,
                    "hysteresis_ratio": float(row[4]) if row[4] else 0.75,
                    "window_days": row[5] if row[5] else 14,
                    "min_sample_count": row[6] if row[6] else 30,
                    "t_up": row[7] if row[7] else 0,
                    "t_down": row[8] if row[8] else 0,
                    "t_up_min": row[9] if row[9] else 100,
                    "t_down_min": row[10] if row[10] else 50,
                    "last_threshold_update": row[11],
                    "threshold_sample_count": row[12] if row[12] else 0,
                }
                for row in results
            ]

    def get_track_online_history(
        self,
        channel_id: str,
        window_days: int
    ) -> List[int]:
        """
        获取赛道历史峰值在线数据

        Args:
            channel_id: 赛道ID
            window_days: 窗口天数

        Returns:
            峰值在线列表
        """
        start_date = datetime.now().date() - timedelta(days=window_days)

        with get_db_session() as session:
            results = session.execute(
                text("""
                    SELECT COALESCE(MAX(hs.online_count), 0) as max_online
                    FROM hourly_snapshot hs
                    JOIN video_channel vc ON hs.bvid = vc.video_bvid
                    WHERE vc.channel_id = :channel_id
                      AND hs.snapshot_time >= :start_date
                    GROUP BY hs.bvid
                """),
                {"channel_id": channel_id, "start_date": start_date}
            ).fetchall()

            return [row[0] for row in results if row[0] > 0]

    def calculate_percentile(self, data: List[int], percentile: float) -> int:
        """
        计算分位数

        Args:
            data: 数据列表
            percentile: 分位数 (0-1)

        Returns:
            分位数值
        """
        if not data:
            return 0

        data_array = np.array(data, dtype=np.int64)
        return int(np.percentile(data_array, percentile * 100))

    def calculate_threshold_for_track(self, channel_id: str) -> Tuple[int, int, int]:
        """
        计算单个赛道的阈值

        Args:
            channel_id: 赛道ID

        Returns:
            (t_up, t_down, sample_count)
        """
        config = self.get_track_config(channel_id)
        if not config:
            return (0, 0, 0)

        # 获取历史数据
        online_history = self.get_track_online_history(
            channel_id,
            config["window_days"]
        )
        sample_count = len(online_history)

        if sample_count >= config["min_sample_count"]:
            # 样本充足，使用动态分位数
            p_up = config["p_up"]
            p_down = config["p_down"]
            hysteresis_ratio = config["hysteresis_ratio"]

            t_up = self.calculate_percentile(online_history, p_up)
            t_down = int(t_up * hysteresis_ratio)

            # 确保不低于保底阈值
            t_up = max(t_up, config["t_up_min"])
            t_down = max(t_down, config["t_down_min"])
        else:
            # 样本不足，使用保底阈值
            t_up = config["t_up_min"]
            t_down = config["t_down_min"]

        return (t_up, t_down, sample_count)

    def update_track_threshold(self, channel_id: str) -> Dict:
        """
        更新赛道阈值

        Args:
            channel_id: 赛道ID

        Returns:
            更新结果
        """
        t_up, t_down, sample_count = self.calculate_threshold_for_track(channel_id)
        now = datetime.now()

        with get_db_session() as session:
            session.execute(
                text("""
                    UPDATE channel_config
                    SET t_up = :t_up,
                        t_down = :t_down,
                        last_threshold_update = :last_update,
                        threshold_sample_count = :sample_count,
                        updated_at = :updated_at
                    WHERE channel_id = :channel_id
                """),
                {
                    "channel_id": channel_id,
                    "t_up": t_up,
                    "t_down": t_down,
                    "last_update": now,
                    "sample_count": sample_count,
                    "updated_at": now,
                }
            )

        return {
            "channel_id": channel_id,
            "t_up": t_up,
            "t_down": t_down,
            "sample_count": sample_count,
        }

    def calculate_all_thresholds(self) -> List[Dict]:
        """
        批量计算所有赛道的阈值

        Returns:
            更新结果列表
        """
        tracks = self.get_all_active_tracks()
        results = []

        for track in tracks:
            result = self.update_track_threshold(track["channel_id"])
            results.append(result)
            print(f"  [{track['channel_id']}] t_up={result['t_up']}, t_down={result['t_down']}, samples={result['sample_count']}")

        return results

    def save_video_daily_peak(self, bvid: str, channel_id: str, max_online: int) -> bool:
        """
        保存视频每日峰值到历史表

        Args:
            bvid: 视频BVID
            channel_id: 赛道ID
            max_online: 最大在线人数

        Returns:
            是否保存成功
        """
        today = datetime.now().date()

        with get_db_session() as session:
            # 检查今日是否已有记录
            existing = session.execute(
                text("""
                    SELECT id, max_online FROM track_online_history
                    WHERE channel_id = :channel_id AND bvid = :bvid AND stat_date = :stat_date
                """),
                {"channel_id": channel_id, "bvid": bvid, "stat_date": today}
            ).fetchone()

            if existing:
                # 更新最大峰值
                if max_online > existing[1]:
                    session.execute(
                        text("""
                            UPDATE track_online_history
                            SET max_online = :max_online
                            WHERE id = :id
                        """),
                        {"max_online": max_online, "id": existing[0]}
                    )
            else:
                # 插入新记录
                session.execute(
                    text("""
                        INSERT INTO track_online_history (channel_id, bvid, max_online, stat_date)
                        VALUES (:channel_id, :bvid, :max_online, :stat_date)
                    """),
                    {
                        "channel_id": channel_id,
                        "bvid": bvid,
                        "max_online": max_online,
                        "stat_date": today,
                    }
                )

            return True

    def get_video_max_online_in_track(self, bvid: str, channel_id: str, window_days: int) -> int:
        """
        获取视频在赛道内的历史最大在线

        Args:
            bvid: 视频BVID
            channel_id: 赛道ID
            window_days: 窗口天数

        Returns:
            最大在线人数
        """
        start_date = datetime.now().date() - timedelta(days=window_days)

        with get_db_session() as session:
            result = session.execute(
                text("""
                    SELECT COALESCE(MAX(online_count), 0)
                    FROM hourly_snapshot
                    WHERE bvid = :bvid
                      AND snapshot_time >= :start_date
                """),
                {"bvid": bvid, "start_date": start_date}
            ).scalar()

            return result or 0


# 全局单例
_track_threshold_service: Optional[TrackAdaptiveThresholdService] = None


def get_track_threshold_service() -> TrackAdaptiveThresholdService:
    """获取赛道阈值服务单例"""
    global _track_threshold_service
    if _track_threshold_service is None:
        _track_threshold_service = TrackAdaptiveThresholdService()
    return _track_threshold_service
