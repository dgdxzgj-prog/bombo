"""
用户数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class UserRole(str, Enum):
    """用户角色枚举"""
    GUEST = "guest"      # 访客，只能浏览
    FREE = "free"        # 免费用户，有限功能
    VIP = "vip"          # VIP用户，全部功能
    ADMIN = "admin"      # 管理员，全部功能+管理


class UserLevel(str, Enum):
    """用户层级枚举"""
    TOURIST = "tourist"      # 游客，未登录
    FREE = "free"           # 免费注册用户
    LIGHT = "light"          # 轻量版 29元/月
    STANDARD = "standard"   # 标准版 89元/月
    PRO = "pro"              # 专业版 299元/月


@dataclass
class User:
    """用户模型"""
    id: Optional[int] = None
    username: str = ""
    email: str = ""
    role: UserRole = UserRole.FREE
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # 分层相关字段
    user_level: UserLevel = UserLevel.FREE    # 用户层级
    trial_count: int = 3                      # 游客剩余试用次数
    subscribe_expire: Optional[datetime] = None  # 订阅到期时间
    subscribe_tier: Optional[str] = None      # 当前订阅套餐 light/standard/pro

    # 权限标志
    can_view_videos: bool = True
    can_search_videos: bool = False
    can_view_ai_analysis: bool = False
    can_manage_channels: bool = False
    can_manage_users: bool = False

    def has_permission(self, permission: str) -> bool:
        """检查用户是否有指定权限"""
        if self.role == UserRole.ADMIN:
            return True

        permission_map = {
            "view_videos": [UserRole.FREE, UserRole.VIP, UserRole.ADMIN],
            "search_videos": [UserRole.FREE, UserRole.VIP, UserRole.ADMIN],
            "view_ai_analysis": [UserRole.VIP, UserRole.ADMIN],
            "manage_channels": [UserRole.VIP, UserRole.ADMIN],
            "manage_users": [UserRole.ADMIN],
        }

        allowed_roles = permission_map.get(permission, [])
        return self.role in allowed_roles

    def is_tourist(self) -> bool:
        """是否为游客"""
        return self.user_level == UserLevel.TOURIST

    def is_free_user(self) -> bool:
        """是否为免费用户"""
        return self.user_level == UserLevel.FREE

    def is_paid_user(self) -> bool:
        """是否为付费用户"""
        return self.user_level in [UserLevel.LIGHT, UserLevel.STANDARD, UserLevel.PRO]

    def is_expired(self) -> bool:
        """订阅是否过期"""
        if self.subscribe_expire is None:
            return False
        return datetime.now() > self.subscribe_expire

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """转换为字典"""
        data = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role.value if isinstance(self.role, UserRole) else self.role,
            "user_level": self.user_level.value if isinstance(self.user_level, UserLevel) else self.user_level,
            "trial_count": self.trial_count,
            "subscribe_expire": self.subscribe_expire.isoformat() if self.subscribe_expire else None,
            "subscribe_tier": self.subscribe_tier,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """从字典创建User对象"""
        role = data.get("role", "free")
        if isinstance(role, str):
            role = UserRole(role)

        user_level = data.get("user_level", "free")
        if isinstance(user_level, str):
            user_level = UserLevel(user_level)

        subscribe_expire = data.get("subscribe_expire")
        if subscribe_expire and isinstance(subscribe_expire, str):
            subscribe_expire = datetime.fromisoformat(subscribe_expire.replace("Z", "+00:00"))

        return cls(
            id=data.get("id"),
            username=data.get("username", ""),
            email=data.get("email", ""),
            role=role,
            user_level=user_level,
            trial_count=data.get("trial_count", 3),
            subscribe_expire=subscribe_expire,
            subscribe_tier=data.get("subscribe_tier"),
            is_active=data.get("is_active", True),
            created_at=data.get("created_at", datetime.now()),
            updated_at=data.get("updated_at", datetime.now()),
        )


@dataclass
class UserSession:
    """用户会话模型"""
    user_id: int
    username: str
    role: UserRole
    token: str
    expires_at: datetime

    def is_expired(self) -> bool:
        """检查会话是否过期"""
        return datetime.now() > self.expires_at

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role.value if isinstance(self.role, UserRole) else self.role,
            "token": self.token,
            "expires_at": self.expires_at.isoformat(),
        }
