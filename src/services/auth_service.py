"""
认证与授权服务
提供用户注册、登录、JWT令牌管理、权限验证
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import hashlib
import hmac
import secrets
import json

from src.models.user import User, UserRole, UserSession
from src.config import settings
from src.utils.database import get_db_session
from sqlalchemy import text


class AuthService:
    """认证授权服务类"""

    # Token配置
    TOKEN_EXPIRE_HOURS = 24
    REFRESH_TOKEN_EXPIRE_DAYS = 7

    def __init__(self):
        self._sessions: Dict[str, UserSession] = {}  # 内存会话存储
        self._secret_key = settings.SECRET_KEY or "default-secret-key"

    def hash_password(self, password: str, salt: Optional[str] = None) -> tuple:
        """密码哈希"""
        if salt is None:
            salt = secrets.token_hex(16)

        pwd_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return pwd_hash.hex(), salt

    def verify_password(self, password: str, pwd_hash: str, salt: str) -> bool:
        """验证密码"""
        computed_hash, _ = self.hash_password(password, salt)
        return hmac.compare_digest(computed_hash, pwd_hash)

    def generate_token(self, user: User) -> str:
        """生成JWT令牌"""
        expires_at = datetime.now() + timedelta(hours=self.TOKEN_EXPIRE_HOURS)

        # 创建会话
        session = UserSession(
            user_id=user.id,
            username=user.username,
            role=user.role,
            token="",  # 稍后生成
            expires_at=expires_at,
        )

        # 生成token (简化版，实际应使用PyJWT)
        token_data = f"{user.id}:{user.username}:{expires_at.timestamp()}:{self._secret_key}"
        token = hashlib.sha256(token_data.encode()).hexdigest()
        session.token = token

        self._sessions[token] = session
        return token

    def verify_token(self, token: str) -> Optional[UserSession]:
        """验证令牌并返回会话"""
        session = self._sessions.get(token)
        if not session:
            return None

        if session.is_expired():
            del self._sessions[token]
            return None

        return session

    def revoke_token(self, token: str) -> bool:
        """撤销令牌"""
        if token in self._sessions:
            del self._sessions[token]
            return True
        return False

    def register_user(
        self,
        username: str,
        password: str,
        email: str,
        role: UserRole = UserRole.FREE
    ) -> Optional[User]:
        """注册新用户"""
        try:
            with get_db_session() as session:
                # 检查用户名是否已存在
                existing = session.execute(
                    text("SELECT id FROM users WHERE username = :username"),
                    {"username": username}
                ).fetchone()

                if existing:
                    return None

                pwd_hash, salt = self.hash_password(password)

                result = session.execute(
                    text("""
                        INSERT INTO users (username, password_hash, salt, email, role, is_active, created_at, updated_at)
                        VALUES (:username, :password_hash, :salt, :email, :role, true, :created_at, :updated_at)
                        RETURNING id
                    """),
                    {
                        "username": username,
                        "password_hash": pwd_hash,
                        "salt": salt,
                        "email": email,
                        "role": role.value if isinstance(role, UserRole) else role,
                        "created_at": datetime.now(),
                        "updated_at": datetime.now(),
                    }
                )
                user_id = result.fetchone()[0]

                return User(
                    id=user_id,
                    username=username,
                    email=email,
                    role=role,
                )
        except Exception as e:
            print(f"Failed to register user: {e}")
            return None

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """用户登录认证"""
        try:
            with get_db_session() as session:
                result = session.execute(
                    text("""
                        SELECT id, username, password_hash, salt, email, role, is_active
                        FROM users WHERE username = :username
                    """),
                    {"username": username}
                ).fetchone()

                if not result:
                    return None

                user_id, username, pwd_hash, salt, email, role, is_active = result

                if not is_active:
                    return None

                if not self.verify_password(password, pwd_hash, salt):
                    return None

                return User(
                    id=user_id,
                    username=username,
                    email=email,
                    role=UserRole(role) if isinstance(role, str) else role,
                    is_active=is_active,
                )
        except Exception as e:
            print(f"Failed to authenticate: {e}")
            return None

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        try:
            with get_db_session() as session:
                result = session.execute(
                    text("""
                        SELECT id, username, email, role, is_active, created_at, updated_at
                        FROM users WHERE id = :user_id
                    """),
                    {"user_id": user_id}
                ).fetchone()

                if not result:
                    return None

                return User(
                    id=result[0],
                    username=result[1],
                    email=result[2],
                    role=UserRole(result[3]) if isinstance(result[3], str) else result[3],
                    is_active=result[4],
                    created_at=result[5],
                    updated_at=result[6],
                )
        except Exception as e:
            print(f"Failed to get user: {e}")
            return None

    def update_user_role(self, user_id: int, new_role: UserRole) -> bool:
        """更新用户角色"""
        try:
            with get_db_session() as session:
                result = session.execute(
                    text("""
                        UPDATE users SET role = :role, updated_at = :updated_at
                        WHERE id = :user_id
                    """),
                    {
                        "role": new_role.value if isinstance(new_role, UserRole) else new_role,
                        "updated_at": datetime.now(),
                        "user_id": user_id,
                    }
                )
                return result.rowcount > 0
        except Exception as e:
            print(f"Failed to update user role: {e}")
            return False

    def deactivate_user(self, user_id: int) -> bool:
        """停用用户"""
        try:
            with get_db_session() as session:
                result = session.execute(
                    text("""
                        UPDATE users SET is_active = false, updated_at = :updated_at
                        WHERE id = :user_id
                    """),
                    {"updated_at": datetime.now(), "user_id": user_id}
                )
                return result.rowcount > 0
        except Exception as e:
            print(f"Failed to deactivate user: {e}")
            return False

    def check_permission(self, token: str, permission: str) -> bool:
        """检查用户权限"""
        session = self.verify_token(token)
        if not session:
            return False

        user = User(
            id=session.user_id,
            username=session.username,
            role=session.role,
        )
        return user.has_permission(permission)

    def get_all_users(self) -> List[User]:
        """获取所有用户"""
        try:
            with get_db_session() as session:
                results = session.execute(
                    text("""
                        SELECT id, username, email, role, is_active, created_at, updated_at
                        FROM users ORDER BY created_at DESC
                    """)
                ).fetchall()

                return [
                    User(
                        id=row[0],
                        username=row[1],
                        email=row[2],
                        role=UserRole(row[3]) if isinstance(row[3], str) else row[3],
                        is_active=row[4],
                        created_at=row[5],
                        updated_at=row[6],
                    )
                    for row in results
                ]
        except Exception as e:
            print(f"Failed to get all users: {e}")
            return []


# 全局单例
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """获取认证服务单例"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
