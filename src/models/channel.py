"""
赛道配置数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ChannelConfig:
    """赛道自适应参数配置模型"""
    channel_id: str
    channel_name: str = ""

    # 爆发层参数
    burst_growth_threshold: float = 0.0   # 爆发增速阈值
    burst_volume_threshold: int = 0       # 播放量基线阈值

    # 体量兜底层参数
    base_growth_threshold: float = 0.0    # 兜底增速阈值
    base_volume_threshold: int = 0        # 兜底播放量阈值

    # 冷启动参数
    cold_start_threshold: int = 0         # 冷启动播放量阈值
    cold_start_hours: int = 72            # 冷启动时间窗口

    # 综合评分权重
    weight_growth: float = 0.4
    weight_volume: float = 0.3
    weight_interaction: float = 0.3

    # 衰退阈值
    decline_growth_threshold: float = 0.0  # 衰退增速阈值

    # 参数版本管理
    param_version: int = 1
    effective_time: Optional[datetime] = None
    sample_size: int = 0
    is_locked: bool = False

    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "burst_growth_threshold": self.burst_growth_threshold,
            "burst_volume_threshold": self.burst_volume_threshold,
            "base_growth_threshold": self.base_growth_threshold,
            "base_volume_threshold": self.base_volume_threshold,
            "cold_start_threshold": self.cold_start_threshold,
            "cold_start_hours": self.cold_start_hours,
            "weight_growth": self.weight_growth,
            "weight_volume": self.weight_volume,
            "weight_interaction": self.weight_interaction,
            "decline_growth_threshold": self.decline_growth_threshold,
            "param_version": self.param_version,
            "effective_time": self.effective_time.isoformat() if self.effective_time else None,
            "sample_size": self.sample_size,
            "is_locked": self.is_locked,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChannelConfig":
        """从字典创建ChannelConfig对象"""
        effective_time = data.get("effective_time")
        if isinstance(effective_time, str):
            effective_time = datetime.fromisoformat(effective_time.replace("Z", "+00:00"))

        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

        return cls(
            channel_id=data["channel_id"],
            channel_name=data.get("channel_name", ""),
            burst_growth_threshold=float(data.get("burst_growth_threshold", 0)),
            burst_volume_threshold=int(data.get("burst_volume_threshold", 0)),
            base_growth_threshold=float(data.get("base_growth_threshold", 0)),
            base_volume_threshold=int(data.get("base_volume_threshold", 0)),
            cold_start_threshold=int(data.get("cold_start_threshold", 0)),
            cold_start_hours=int(data.get("cold_start_hours", 72)),
            weight_growth=float(data.get("weight_growth", 0.4)),
            weight_volume=float(data.get("weight_volume", 0.3)),
            weight_interaction=float(data.get("weight_interaction", 0.3)),
            decline_growth_threshold=float(data.get("decline_growth_threshold", 0)),
            param_version=int(data.get("param_version", 1)),
            effective_time=effective_time,
            sample_size=int(data.get("sample_size", 0)),
            is_locked=bool(data.get("is_locked", False)),
            created_at=created_at or datetime.now(),
            updated_at=updated_at or datetime.now(),
        )
