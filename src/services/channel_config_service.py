"""
赛道配置服务层
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import text

from src.models.channel import ChannelConfig
from src.utils.database import get_db_session


class ChannelConfigService:
    """赛道配置服务类"""

    def add_channel(self, config: ChannelConfig) -> ChannelConfig:
        """
        添加赛道配置
        如果channel_id已存在则抛出异常
        """
        with get_db_session() as session:
            # 检查是否已存在
            result = session.execute(
                text("SELECT channel_id FROM channel_config WHERE channel_id = :channel_id OR channel_name = :channel_id"),
                {"channel_id": config.channel_id}
            ).fetchone()

            if result:
                raise ValueError(f"Channel with id {config.channel_id} already exists")

            now = datetime.now()
            session.execute(
                text("""
                    INSERT INTO channel_config
                    (channel_id, channel_name, burst_growth_threshold, burst_volume_threshold,
                     base_growth_threshold, base_volume_threshold, cold_start_threshold,
                     cold_start_hours, weight_growth, weight_volume, weight_interaction,
                     decline_growth_threshold, param_version, effective_time, sample_size,
                     is_locked, created_at, updated_at)
                    VALUES
                    (:channel_id, :channel_name, :burst_growth_threshold, :burst_volume_threshold,
                     :base_growth_threshold, :base_volume_threshold, :cold_start_threshold,
                     :cold_start_hours, :weight_growth, :weight_volume, :weight_interaction,
                     :decline_growth_threshold, :param_version, :effective_time, :sample_size,
                     :is_locked, :created_at, :updated_at)
                """),
                {
                    "channel_id": config.channel_id,
                    "channel_name": config.channel_name,
                    "burst_growth_threshold": config.burst_growth_threshold,
                    "burst_volume_threshold": config.burst_volume_threshold,
                    "base_growth_threshold": config.base_growth_threshold,
                    "base_volume_threshold": config.base_volume_threshold,
                    "cold_start_threshold": config.cold_start_threshold,
                    "cold_start_hours": config.cold_start_hours,
                    "weight_growth": config.weight_growth,
                    "weight_volume": config.weight_volume,
                    "weight_interaction": config.weight_interaction,
                    "decline_growth_threshold": config.decline_growth_threshold,
                    "param_version": config.param_version,
                    "effective_time": config.effective_time,
                    "sample_size": config.sample_size,
                    "is_locked": config.is_locked,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            return config

    def get_channel_by_id(self, channel_id: str) -> Optional[ChannelConfig]:
        """根据channel_id或channel_name获取赛道配置（临时支持中文名称查询）"""
        with get_db_session() as session:
            result = session.execute(
                text("""
                    SELECT channel_id, channel_name,
                           burst_growth_threshold, burst_volume_threshold,
                           base_growth_threshold, base_volume_threshold,
                           cold_start_threshold, cold_start_hours,
                           weight_growth, weight_volume, weight_interaction,
                           decline_growth_threshold, param_version, effective_time,
                           sample_size, is_locked, created_at, updated_at
                    FROM channel_config
                    WHERE channel_id = :channel_id OR channel_name = :channel_id
                """),
                {"channel_id": channel_id}
            ).fetchone()

            if result is None:
                return None

            return self._row_to_config(result)

    def get_all_channels(self) -> List[ChannelConfig]:
        """获取所有赛道配置"""
        with get_db_session() as session:
            results = session.execute(
                text("""
                    SELECT channel_id, channel_name,
                           burst_growth_threshold, burst_volume_threshold,
                           base_growth_threshold, base_volume_threshold,
                           cold_start_threshold, cold_start_hours,
                           weight_growth, weight_volume, weight_interaction,
                           decline_growth_threshold, param_version, effective_time,
                           sample_size, is_locked, created_at, updated_at
                    FROM channel_config
                    ORDER BY channel_id
                """)
            ).fetchall()

            return [self._row_to_config(row) for row in results]

    def get_unlocked_channels(self) -> List[ChannelConfig]:
        """获取未锁定的赛道配置"""
        with get_db_session() as session:
            results = session.execute(
                text("""
                    SELECT channel_id, channel_name,
                           burst_growth_threshold, burst_volume_threshold,
                           base_growth_threshold, base_volume_threshold,
                           cold_start_threshold, cold_start_hours,
                           weight_growth, weight_volume, weight_interaction,
                           decline_growth_threshold, param_version, effective_time,
                           sample_size, is_locked, created_at, updated_at
                    FROM channel_config
                    WHERE is_locked = FALSE
                    ORDER BY channel_id
                """)
            ).fetchall()

            return [self._row_to_config(row) for row in results]

    def update_channel(self, channel_id: str, **kwargs) -> bool:
        """更新赛道配置"""
        if not kwargs:
            return False

        kwargs["updated_at"] = datetime.now()
        kwargs["channel_id"] = channel_id

        set_clause = ", ".join([f"{k} = :{k}" for k in kwargs.keys()])

        with get_db_session() as session:
            result = session.execute(
                text(f"UPDATE channel_config SET {set_clause} WHERE channel_id = :channel_id OR channel_name = :channel_id"),
                kwargs
            )
            return result.rowcount > 0

    def update_channel_params(
        self,
        channel_id: str,
        burst_growth_threshold: Optional[float] = None,
        burst_volume_threshold: Optional[int] = None,
        base_growth_threshold: Optional[float] = None,
        base_volume_threshold: Optional[int] = None,
        cold_start_threshold: Optional[int] = None,
        cold_start_hours: Optional[int] = None,
        weight_growth: Optional[float] = None,
        weight_volume: Optional[float] = None,
        weight_interaction: Optional[float] = None,
        decline_growth_threshold: Optional[float] = None,
    ) -> bool:
        """更新赛道判定参数"""
        update_data = {"updated_at": datetime.now(), "channel_id": channel_id}

        params_mapping = [
            ("burst_growth_threshold", burst_growth_threshold),
            ("burst_volume_threshold", burst_volume_threshold),
            ("base_growth_threshold", base_growth_threshold),
            ("base_volume_threshold", base_volume_threshold),
            ("cold_start_threshold", cold_start_threshold),
            ("cold_start_hours", cold_start_hours),
            ("weight_growth", weight_growth),
            ("weight_volume", weight_volume),
            ("weight_interaction", weight_interaction),
            ("decline_growth_threshold", decline_growth_threshold),
        ]

        for key, value in params_mapping:
            if value is not None:
                update_data[key] = value

        if len(update_data) == 2:  # 只有updated_at和channel_id
            return False

        set_clause = ", ".join([f"{k} = :{k}" for k in update_data.keys()])

        with get_db_session() as session:
            result = session.execute(
                text(f"UPDATE channel_config SET {set_clause} WHERE channel_id = :channel_id OR channel_name = :channel_id"),
                update_data
            )
            return result.rowcount > 0

    def lock_channel(self, channel_id: str) -> bool:
        """锁定赛道参数"""
        return self.update_channel(channel_id, is_locked=True)

    def unlock_channel(self, channel_id: str) -> bool:
        """解锁赛道参数"""
        return self.update_channel(channel_id, is_locked=False)

    def increment_version(self, channel_id: str) -> bool:
        """增加参数版本号"""
        with get_db_session() as session:
            # 先获取当前版本
            result = session.execute(
                text("SELECT param_version FROM channel_config WHERE channel_id = :channel_id OR channel_name = :channel_id"),
                {"channel_id": channel_id}
            ).fetchone()

            if not result:
                return False

            new_version = result[0] + 1
            now = datetime.now()

            session.execute(
                text("""
                    UPDATE channel_config
                    SET param_version = :param_version,
                        effective_time = :effective_time,
                        updated_at = :updated_at
                    WHERE channel_id = :channel_id OR channel_name = :channel_id
                """),
                {
                    "param_version": new_version,
                    "effective_time": now,
                    "updated_at": now,
                    "channel_id": channel_id,
                }
            )
            return True

    def update_calibration_result(
        self,
        channel_id: str,
        burst_growth_threshold: float,
        burst_volume_threshold: int,
        base_growth_threshold: float,
        base_volume_threshold: int,
        cold_start_threshold: int,
        decline_growth_threshold: float,
        sample_size: int,
    ) -> bool:
        """更新校准结果"""
        if not self.increment_version(channel_id):
            return False

        return self.update_channel_params(
            channel_id=channel_id,
            burst_growth_threshold=burst_growth_threshold,
            burst_volume_threshold=burst_volume_threshold,
            base_growth_threshold=base_growth_threshold,
            base_volume_threshold=base_volume_threshold,
            cold_start_threshold=cold_start_threshold,
            decline_growth_threshold=decline_growth_threshold,
        ) and self.update_channel(channel_id, sample_size=sample_size)

    def delete_channel(self, channel_id: str) -> bool:
        """删除赛道配置"""
        with get_db_session() as session:
            result = session.execute(
                text("DELETE FROM channel_config WHERE channel_id = :channel_id OR channel_name = :channel_id"),
                {"channel_id": channel_id}
            )
            return result.rowcount > 0

    def _row_to_config(self, row) -> ChannelConfig:
        """将数据库行转换为ChannelConfig对象"""
        return ChannelConfig(
            channel_id=row[0],
            channel_name=row[1] or "",
            burst_growth_threshold=float(row[2] or 0),
            burst_volume_threshold=int(row[3] or 0),
            base_growth_threshold=float(row[4] or 0),
            base_volume_threshold=int(row[5] or 0),
            cold_start_threshold=int(row[6] or 0),
            cold_start_hours=int(row[7] or 72),
            weight_growth=float(row[8] or 0.4),
            weight_volume=float(row[9] or 0.3),
            weight_interaction=float(row[10] or 0.3),
            decline_growth_threshold=float(row[11] or 0),
            param_version=int(row[12] or 1),
            effective_time=row[13],
            sample_size=int(row[14] or 0),
            is_locked=bool(row[15] or False),
            created_at=row[16],
            updated_at=row[17],
        )
