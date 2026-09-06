"""
用户关键词数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class UserKeyword:
    """用户关键词模型"""
    id: Optional[int] = None
    user_id: str = ""
    keyword: str = ""
    channel: str = "其他"
    status: int = 1  # 1=监控中, 0=已停用
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def is_active(self) -> bool:
        """是否处于监控中状态"""
        return self.status == 1

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "keyword": self.keyword,
            "channel": self.channel,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserKeyword":
        """从字典创建UserKeyword对象"""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

        return cls(
            id=data.get("id"),
            user_id=data.get("user_id", ""),
            keyword=data.get("keyword", ""),
            channel=data.get("channel", "其他"),
            status=data.get("status", 1),
            created_at=created_at or datetime.now(),
            updated_at=updated_at or datetime.now(),
        )
