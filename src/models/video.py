"""
视频数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class VideoStatus(str, Enum):
    """视频监控状态枚举"""
    MONITORING = "monitoring"  # 监控中
    FEATURED = "featured"      # 已上榜
    DECLINED = "declined"      # 已衰退


@dataclass
class Video:
    """视频数据模型"""
    bvid: str
    title: str = ""
    author: str = ""
    channel: str = ""
    keyword: str = ""

    # 播放量与增速
    view_yesterday: int = 0
    view_today: int = 0
    growth_rate: float = 0.0

    # 互动数据
    like_count: int = 0
    favorite_count: int = 0
    reply_count: int = 0
    online_count: int = 0  # 在线观看人数

    # 视频元数据
    pubdate: Optional[datetime] = None
    cover_url: Optional[str] = None

    # 状态管理
    status: VideoStatus = VideoStatus.MONITORING

    # 时间戳
    first_seen: datetime = field(default_factory=datetime.now)
    last_collected: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # 数据库主键
    id: Optional[int] = None

    def calculate_growth_rate(self) -> float:
        """
        计算播放增速
        公式: (今日播放量 - 昨日播放量) / 昨日播放量 * 100%
        如果昨日播放量为0，返回0
        """
        if self.view_yesterday == 0:
            return 0.0
        return round((self.view_today - self.view_yesterday) / self.view_yesterday * 100, 2)

    def roll_views(self) -> None:
        """滚动播放数据：昨日=今日，今日=0"""
        self.view_yesterday = self.view_today
        self.view_today = 0

    def is_published_within_hours(self, hours: int) -> bool:
        """判断视频是否在指定小时内发布"""
        if self.pubdate is None:
            return False
        delta = datetime.now() - self.pubdate
        return delta.total_seconds() <= hours * 3600

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "bvid": self.bvid,
            "title": self.title,
            "author": self.author,
            "channel": self.channel,
            "keyword": self.keyword,
            "view_yesterday": self.view_yesterday,
            "view_today": self.view_today,
            "growth_rate": self.growth_rate,
            "like_count": self.like_count,
            "favorite_count": self.favorite_count,
            "reply_count": self.reply_count,
            "online_count": self.online_count,
            "pubdate": self.pubdate.isoformat() if self.pubdate else None,
            "cover_url": self.cover_url,
            "status": self.status.value if isinstance(self.status, VideoStatus) else self.status,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_collected": self.last_collected.isoformat() if self.last_collected else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Video":
        """从字典创建Video对象"""
        status = data.get("status", "monitoring")
        if isinstance(status, str):
            status = VideoStatus(status)

        pubdate = data.get("pubdate")
        if isinstance(pubdate, str):
            pubdate = datetime.fromisoformat(pubdate.replace("Z", "+00:00"))

        first_seen = data.get("first_seen")
        if isinstance(first_seen, str):
            first_seen = datetime.fromisoformat(first_seen.replace("Z", "+00:00"))

        last_collected = data.get("last_collected")
        if isinstance(last_collected, str):
            last_collected = datetime.fromisoformat(last_collected.replace("Z", "+00:00"))

        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

        return cls(
            id=data.get("id"),
            bvid=data["bvid"],
            title=data.get("title", ""),
            author=data.get("author", ""),
            channel=data.get("channel", ""),
            keyword=data.get("keyword", ""),
            view_yesterday=data.get("view_yesterday", 0),
            view_today=data.get("view_today", 0),
            growth_rate=float(data.get("growth_rate", 0)),
            like_count=data.get("like_count", 0),
            favorite_count=data.get("favorite_count", 0),
            reply_count=data.get("reply_count", 0),
            online_count=data.get("online_count", 0),
            pubdate=pubdate,
            cover_url=data.get("cover_url"),
            status=status,
            first_seen=first_seen or datetime.now(),
            last_collected=last_collected,
            created_at=created_at or datetime.now(),
            updated_at=updated_at or datetime.now(),
        )
