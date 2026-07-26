"""
视频-赛道关联模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class VideoChannelStatus(str, Enum):
    """视频在某个赛道中的状态枚举"""
    MONITORING = "monitoring"  # 监控中
    FEATURED = "featured"      # 已上榜
    DECLINED = "declined"      # 已衰退


@dataclass
class VideoChannel:
    """视频-赛道关联模型"""
    video_bvid: str
    channel_id: str
    is_primary: bool = True
    status: VideoChannelStatus = VideoChannelStatus.MONITORING
    created_at: datetime = field(default_factory=datetime.now)

    # 数据库主键
    id: Optional[int] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "video_bvid": self.video_bvid,
            "channel_id": self.channel_id,
            "is_primary": self.is_primary,
            "status": self.status.value if isinstance(self.status, VideoChannelStatus) else self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VideoChannel":
        """从字典创建VideoChannel对象"""
        status = data.get("status", "monitoring")
        if isinstance(status, str):
            status = VideoChannelStatus(status)

        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        return cls(
            id=data.get("id"),
            video_bvid=data["video_bvid"],
            channel_id=data["channel_id"],
            is_primary=data.get("is_primary", True),
            status=status,
            created_at=created_at or datetime.now(),
        )
