"""
用户自选赛道视频数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List


def _format_datetime(dt) -> Optional[str]:
    """将datetime对象或字符串转换为ISO格式字符串"""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    if isinstance(dt, str):
        try:
            if "T" in dt or " " in dt:
                return dt
            parsed = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            return parsed.isoformat()
        except (ValueError, AttributeError):
            return dt
    return str(dt)


class UserVideoStatus(str, Enum):
    """用户自选赛道视频状态枚举"""
    MONITORING = "monitoring"  # 监控中
    FEATURED = "featured"      # 已上榜
    DECLINED = "declined"      # 已衰退


@dataclass
class UserMonitorVideo:
    """用户自选赛道视频数据模型"""
    bvid: str
    title: str = ""
    author: str = ""
    author_mid: Optional[str] = None
    channel: str = "其他"
    keyword: str = ""

    # 播放量与增速
    view_yesterday: int = 0
    view_today: int = 0
    growth_rate: float = 0.0

    # 互动数据
    like_count: int = 0
    favorite_count: int = 0
    reply_count: int = 0
    coin_count: int = 0
    share_count: int = 0
    danmu_count: int = 0
    online_count: int = 0
    max_online_today: int = 0

    # 视频元数据
    pubdate: Optional[datetime] = None
    cover_url: Optional[str] = None
    duration: int = 0
    tags: Optional[List[str]] = None

    # 状态管理
    status: UserVideoStatus = UserVideoStatus.MONITORING

    # 时间戳
    first_seen: datetime = field(default_factory=datetime.now)
    last_collected: Optional[datetime] = None
    featured_at: Optional[datetime] = None
    declined_at: Optional[datetime] = None
    declined_reason: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # 数据库主键
    id: Optional[int] = None

    def calculate_growth_rate(self) -> float:
        """
        计算播放增速
        公式: (今日播放量 - 昨日播放量) / 昨日播放量 * 100%
        """
        if self.view_yesterday == 0:
            return 0.0
        return round((self.view_today - self.view_yesterday) / self.view_yesterday * 100, 2)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "bvid": self.bvid,
            "title": self.title,
            "author": self.author,
            "author_mid": self.author_mid,
            "channel": self.channel,
            "keyword": self.keyword,
            "view_yesterday": self.view_yesterday,
            "view_today": self.view_today,
            "growth_rate": self.growth_rate,
            "like_count": self.like_count,
            "favorite_count": self.favorite_count,
            "reply_count": self.reply_count,
            "coin_count": self.coin_count,
            "share_count": self.share_count,
            "danmu_count": self.danmu_count,
            "online_count": self.online_count,
            "max_online_today": self.max_online_today,
            "pubdate": _format_datetime(self.pubdate),
            "cover_url": self.cover_url,
            "duration": self.duration,
            "tags": self.tags,
            "status": self.status.value if isinstance(self.status, UserVideoStatus) else self.status,
            "first_seen": _format_datetime(self.first_seen),
            "last_collected": _format_datetime(self.last_collected),
            "featured_at": _format_datetime(self.featured_at),
            "declined_at": _format_datetime(self.declined_at),
            "declined_reason": self.declined_reason,
            "created_at": _format_datetime(self.created_at),
            "updated_at": _format_datetime(self.updated_at),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserMonitorVideo":
        """从字典创建UserMonitorVideo对象"""
        status = data.get("status", "monitoring")
        if isinstance(status, str):
            status = UserVideoStatus(status)

        pubdate = data.get("pubdate")
        if isinstance(pubdate, str):
            pubdate = datetime.fromisoformat(pubdate.replace("Z", "+00:00"))

        first_seen = data.get("first_seen")
        if isinstance(first_seen, str):
            first_seen = datetime.fromisoformat(first_seen.replace("Z", "+00:00"))

        last_collected = data.get("last_collected")
        if isinstance(last_collected, str):
            last_collected = datetime.fromisoformat(last_collected.replace("Z", "+00:00"))

        featured_at = data.get("featured_at")
        if isinstance(featured_at, str):
            featured_at = datetime.fromisoformat(featured_at.replace("Z", "+00:00"))

        declined_at = data.get("declined_at")
        if isinstance(declined_at, str):
            declined_at = datetime.fromisoformat(declined_at.replace("Z", "+00:00"))

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
            author_mid=data.get("author_mid"),
            channel=data.get("channel", "其他"),
            keyword=data.get("keyword", ""),
            view_yesterday=data.get("view_yesterday", 0),
            view_today=data.get("view_today", 0),
            growth_rate=float(data.get("growth_rate", 0)),
            like_count=data.get("like_count", 0),
            favorite_count=data.get("favorite_count", 0),
            reply_count=data.get("reply_count", 0),
            coin_count=data.get("coin_count", 0),
            share_count=data.get("share_count", 0),
            danmu_count=data.get("danmu_count", 0),
            online_count=data.get("online_count", 0),
            max_online_today=data.get("max_online_today", 0),
            pubdate=pubdate,
            cover_url=data.get("cover_url"),
            duration=data.get("duration", 0),
            tags=data.get("tags"),
            status=status,
            first_seen=first_seen or datetime.now(),
            last_collected=last_collected,
            featured_at=featured_at,
            declined_at=declined_at,
            declined_reason=data.get("declined_reason"),
            created_at=created_at or datetime.now(),
            updated_at=updated_at or datetime.now(),
        )
