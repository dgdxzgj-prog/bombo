"""
用户视频订阅数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class UserVideoSubscription:
    """用户视频订阅模型"""
    id: Optional[int] = None
    user_id: str = ""
    bvid: str = ""
    keyword: str = ""
    subscribed_at: datetime = field(default_factory=datetime.now)
    status: int = 1  # 1=监控中, 0=已取消

    @property
    def is_active(self) -> bool:
        """是否处于监控中状态"""
        return self.status == 1

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "bvid": self.bvid,
            "keyword": self.keyword,
            "subscribed_at": self.subscribed_at.isoformat() if self.subscribed_at else None,
            "status": self.status,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserVideoSubscription":
        """从字典创建UserVideoSubscription对象"""
        subscribed_at = data.get("subscribed_at")
        if isinstance(subscribed_at, str):
            subscribed_at = datetime.fromisoformat(subscribed_at.replace("Z", "+00:00"))

        return cls(
            id=data.get("id"),
            user_id=data.get("user_id", ""),
            bvid=data.get("bvid", ""),
            keyword=data.get("keyword", ""),
            subscribed_at=subscribed_at or datetime.now(),
            status=data.get("status", 1),
        )
