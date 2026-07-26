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
    status: str = "active"  # 赛道状态: active, inactive
    sort_order: int = 0  # 排序值

    # 赛道自适应阈值参数
    p_up: float = 0.90              # 爆款上线分位数
    p_down: float = 0.70            # 衰退下线分位数
    hysteresis_ratio: float = 0.75   # 滞回系数 T_down = T_up * hysteresis_ratio
    window_days: int = 14           # 样本窗口天数
    min_sample_count: int = 30      # 最小样本数量
    t_up: int = 0                   # 爆款阈值（峰值在线人数）
    t_down: int = 0                 # 衰退阈值
    t_up_min: int = 100             # 爆款阈值保底值
    t_down_min: int = 50            # 衰退阈值保底值
    last_threshold_update: Optional[datetime] = None  # 最后阈值更新时间
    threshold_sample_count: int = 0  # 阈值计算样本数

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
            "status": self.status,
            "sort_order": self.sort_order,
            # 赛道自适应阈值参数
            "p_up": self.p_up,
            "p_down": self.p_down,
            "hysteresis_ratio": self.hysteresis_ratio,
            "window_days": self.window_days,
            "min_sample_count": self.min_sample_count,
            "t_up": self.t_up,
            "t_down": self.t_down,
            "t_up_min": self.t_up_min,
            "t_down_min": self.t_down_min,
            "last_threshold_update": self.last_threshold_update.isoformat() if self.last_threshold_update else None,
            "threshold_sample_count": self.threshold_sample_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChannelConfig":
        """从字典创建ChannelConfig对象"""
        effective_time = data.get("effective_time")
        if isinstance(effective_time, str):
            effective_time = datetime.fromisoformat(effective_time.replace("Z", "+00:00"))

        last_threshold_update = data.get("last_threshold_update")
        if isinstance(last_threshold_update, str):
            last_threshold_update = datetime.fromisoformat(last_threshold_update.replace("Z", "+00:00"))

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
            status=data.get("status", "active"),
            sort_order=int(data.get("sort_order", 0)),
            # 赛道自适应阈值参数
            p_up=float(data.get("p_up", 0.90)),
            p_down=float(data.get("p_down", 0.70)),
            hysteresis_ratio=float(data.get("hysteresis_ratio", 0.75)),
            window_days=int(data.get("window_days", 14)),
            min_sample_count=int(data.get("min_sample_count", 30)),
            t_up=int(data.get("t_up", 0)),
            t_down=int(data.get("t_down", 0)),
            t_up_min=int(data.get("t_up_min", 100)),
            t_down_min=int(data.get("t_down_min", 50)),
            last_threshold_update=last_threshold_update,
            threshold_sample_count=int(data.get("threshold_sample_count", 0)),
            created_at=created_at or datetime.now(),
            updated_at=updated_at or datetime.now(),
        )
