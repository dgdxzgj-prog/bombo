"""
UP主（作者）数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class AuthorInfo:
    """UP主信息数据模型"""
    mid: str = ""  # B站用户ID
    name: str = ""
    avatar: Optional[str] = None

    # 粉丝与关注数据
    fans: int = 0           # 粉丝数
    following: int = 0       # 关注数

    # 作品统计
    archive_count: int = 0  # 投稿作品数（审核通过）

    # 扩展统计
    total_view: int = 0     # 总播放
    total_liked: int = 0    # 总获赞

    # 时间戳
    first_collected: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)

    # 数据库主键
    id: Optional[int] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "mid": self.mid,
            "name": self.name,
            "avatar": self.avatar,
            "fans": self.fans,
            "following": self.following,
            "archive_count": self.archive_count,
            "total_view": self.total_view,
            "total_liked": self.total_liked,
            "first_collected": self.first_collected.isoformat() if self.first_collected else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AuthorInfo":
        """从字典创建AuthorInfo对象"""
        def parse_datetime(value):
            if isinstance(value, str):
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            return value

        return cls(
            id=data.get("id"),
            mid=data.get("mid", ""),
            name=data.get("name", ""),
            avatar=data.get("avatar"),
            fans=data.get("fans", 0),
            following=data.get("following", 0),
            archive_count=data.get("archive_count", 0),
            total_view=data.get("total_view", 0),
            total_liked=data.get("total_liked", 0),
            first_collected=parse_datetime(data.get("first_collected")) or datetime.now(),
            last_updated=parse_datetime(data.get("last_updated")) or datetime.now(),
            created_at=parse_datetime(data.get("created_at")) or datetime.now(),
        )
