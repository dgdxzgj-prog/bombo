"""
认证与权限系统单元测试
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from src.models.user import User, UserRole, UserSession
from src.services.auth_service import AuthService, get_auth_service


class TestUserRole:
    """UserRole枚举测试类"""

    def test_role_values(self):
        """测试角色枚举值"""
        assert UserRole.GUEST.value == "guest"
        assert UserRole.FREE.value == "free"
        assert UserRole.VIP.value == "vip"
        assert UserRole.ADMIN.value == "admin"


class TestUser:
    """User模型测试类"""

    def test_has_permission_admin(self):
        """测试管理员拥有所有权限"""
        user = User(id=1, username="admin", role=UserRole.ADMIN)

        assert user.has_permission("view_videos") is True
        assert user.has_permission("search_videos") is True
        assert user.has_permission("view_ai_analysis") is True
        assert user.has_permission("manage_channels") is True
        assert user.has_permission("manage_users") is True

    def test_has_permission_vip(self):
        """测试VIP用户权限"""
        user = User(id=1, username="vip", role=UserRole.VIP)

        assert user.has_permission("view_videos") is True
        assert user.has_permission("search_videos") is True
        assert user.has_permission("view_ai_analysis") is True
        assert user.has_permission("manage_channels") is True
        assert user.has_permission("manage_users") is False

    def test_has_permission_free(self):
        """测试免费用户权限"""
        user = User(id=1, username="free", role=UserRole.FREE)

        assert user.has_permission("view_videos") is True
        assert user.has_permission("search_videos") is True
        assert user.has_permission("view_ai_analysis") is False
        assert user.has_permission("manage_channels") is False
        assert user.has_permission("manage_users") is False

    def test_has_permission_guest(self):
        """测试访客权限"""
        user = User(id=1, username="guest", role=UserRole.GUEST)

        assert user.has_permission("view_videos") is False
        assert user.has_permission("search_videos") is False
        assert user.has_permission("view_ai_analysis") is False
        assert user.has_permission("manage_channels") is False
        assert user.has_permission("manage_users") is False

    def test_to_dict(self):
        """测试转换为字典"""
        user = User(
            id=1,
            username="test",
            email="test@example.com",
            role=UserRole.VIP,
            is_active=True,
        )

        d = user.to_dict()
        assert d["id"] == 1
        assert d["username"] == "test"
        assert d["email"] == "test@example.com"
        assert d["role"] == "vip"
        assert d["is_active"] is True

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "id": 1,
            "username": "test",
            "email": "test@example.com",
            "role": "vip",
            "is_active": True,
        }

        user = User.from_dict(data)
        assert user.id == 1
        assert user.username == "test"
        assert user.role == UserRole.VIP


class TestUserSession:
    """UserSession模型测试类"""

    def test_is_expired_false(self):
        """测试会话未过期"""
        session = UserSession(
            user_id=1,
            username="test",
            role=UserRole.FREE,
            token="abc123",
            expires_at=datetime.now() + timedelta(hours=1),
        )
        assert session.is_expired() is False

    def test_is_expired_true(self):
        """测试会话已过期"""
        session = UserSession(
            user_id=1,
            username="test",
            role=UserRole.FREE,
            token="abc123",
            expires_at=datetime.now() - timedelta(hours=1),
        )
        assert session.is_expired() is True

    def test_to_dict(self):
        """测试转换为字典"""
        expires = datetime.now() + timedelta(hours=24)
        session = UserSession(
            user_id=1,
            username="test",
            role=UserRole.FREE,
            token="abc123",
            expires_at=expires,
        )

        d = session.to_dict()
        assert d["user_id"] == 1
        assert d["username"] == "test"
        assert d["role"] == "free"
        assert d["token"] == "abc123"


class TestAuthService:
    """AuthService测试类"""

    def setup_method(self):
        """测试前置设置"""
        self.service = AuthService()

    def test_hash_password(self):
        """测试密码哈希"""
        pwd_hash, salt = self.service.hash_password("test123")

        assert pwd_hash is not None
        assert salt is not None
        assert len(pwd_hash) == 64  # SHA256 hex length
        assert len(salt) == 32  # 16 bytes hex

    def test_verify_password_correct(self):
        """测试正确密码验证"""
        pwd_hash, salt = self.service.hash_password("test123")

        assert self.service.verify_password("test123", pwd_hash, salt) is True

    def test_verify_password_incorrect(self):
        """测试错误密码验证"""
        pwd_hash, salt = self.service.hash_password("test123")

        assert self.service.verify_password("wrongpassword", pwd_hash, salt) is False

    def test_generate_and_verify_token(self):
        """测试生成和验证令牌"""
        user = User(id=1, username="test", role=UserRole.FREE)

        token = self.service.generate_token(user)
        assert token is not None

        session = self.service.verify_token(token)
        assert session is not None
        assert session.user_id == 1
        assert session.username == "test"

    def test_verify_invalid_token(self):
        """测试无效令牌"""
        session = self.service.verify_token("invalid_token")
        assert session is None

    def test_revoke_token(self):
        """测试撤销令牌"""
        user = User(id=1, username="test", role=UserRole.FREE)

        token = self.service.generate_token(user)
        assert self.service.verify_token(token) is not None

        self.service.revoke_token(token)
        assert self.service.verify_token(token) is None

    def test_check_permission_true(self):
        """测试权限检查-有权限"""
        user = User(id=1, username="test", role=UserRole.VIP)
        token = self.service.generate_token(user)

        assert self.service.check_permission(token, "view_ai_analysis") is True

    def test_check_permission_false(self):
        """测试权限检查-无权限"""
        user = User(id=1, username="test", role=UserRole.FREE)
        token = self.service.generate_token(user)

        assert self.service.check_permission(token, "view_ai_analysis") is False

    def test_check_permission_invalid_token(self):
        """测试权限检查-无效令牌"""
        assert self.service.check_permission("invalid_token", "view_videos") is False

    @patch("src.services.auth_service.get_db_session")
    def test_authenticate_success(self, mock_get_session):
        """测试登录成功"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        pwd_hash, salt = self.service.hash_password("test123")

        mock_session.execute.return_value.fetchone.return_value = (
            1, "testuser", pwd_hash, salt, "test@example.com", "free", True
        )

        user = self.service.authenticate("testuser", "test123")

        assert user is not None
        assert user.username == "testuser"

    @patch("src.services.auth_service.get_db_session")
    def test_authenticate_wrong_password(self, mock_get_session):
        """测试密码错误"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        pwd_hash, salt = self.service.hash_password("test123")

        mock_session.execute.return_value.fetchone.return_value = (
            1, "testuser", pwd_hash, salt, "test@example.com", "free", True
        )

        user = self.service.authenticate("testuser", "wrongpassword")
        assert user is None

    @patch("src.services.auth_service.get_db_session")
    def test_authenticate_user_not_found(self, mock_get_session):
        """测试用户不存在"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_session.execute.return_value.fetchone.return_value = None

        user = self.service.authenticate("nonexistent", "password")
        assert user is None

    @patch("src.services.auth_service.get_db_session")
    def test_get_user_by_id(self, mock_get_session):
        """测试根据ID获取用户"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_session.execute.return_value.fetchone.return_value = (
            1, "testuser", "test@example.com", "vip", True,
            datetime.now(), datetime.now()
        )

        user = self.service.get_user_by_id(1)

        assert user is not None
        assert user.id == 1
        assert user.username == "testuser"
        assert user.role == UserRole.VIP

    @patch("src.services.auth_service.get_db_session")
    def test_get_user_by_id_not_found(self, mock_get_session):
        """测试根据ID获取用户不存在"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_session.execute.return_value.fetchone.return_value = None

        user = self.service.get_user_by_id(999)
        assert user is None

    @patch("src.services.auth_service.get_db_session")
    def test_update_user_role(self, mock_get_session):
        """测试更新用户角色"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        success = self.service.update_user_role(1, UserRole.ADMIN)
        assert success is True

    @patch("src.services.auth_service.get_db_session")
    def test_get_all_users(self, mock_get_session):
        """测试获取所有用户"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_session.execute.return_value.fetchall.return_value = [
            (1, "user1", "u1@example.com", "free", True, datetime.now(), datetime.now()),
            (2, "user2", "u2@example.com", "vip", True, datetime.now(), datetime.now()),
        ]

        users = self.service.get_all_users()

        assert len(users) == 2
        assert users[0].username == "user1"
        assert users[1].role == UserRole.VIP


class TestGetAuthService:
    """认证服务单例测试类"""

    def test_get_auth_service(self):
        """测试获取认证服务单例"""
        service1 = get_auth_service()
        service2 = get_auth_service()
        assert service1 is service2
