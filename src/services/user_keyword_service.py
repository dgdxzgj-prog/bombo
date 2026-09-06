"""
用户关键词服务
"""
import re
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import text

from src.models.user_keyword import UserKeyword
from src.models.user_monitor_video import UserVideoStatus
from src.utils.database import get_db_session


class UserKeywordService:
    """用户关键词服务类"""

    # 验证配置
    MIN_KEYWORD_LENGTH = 2
    MAX_KEYWORD_LENGTH = 20
    MAX_KEYWORDS_PER_USER = 20
    SPECIAL_CHAR_PATTERN = re.compile(r'[@#￥%^&*()_+=\[\]{}|\\:;"\'<>,.?/~`]')

    def validate_keyword(self, keyword: str) -> Tuple[bool, str]:
        """
        验证关键词格式
        返回: (是否通过, 错误信息)
        """
        keyword = keyword.strip()

        if len(keyword) < self.MIN_KEYWORD_LENGTH:
            return False, f"关键词长度不能少于{self.MIN_KEYWORD_LENGTH}个字符"

        if len(keyword) > self.MAX_KEYWORD_LENGTH:
            return False, f"关键词长度不能超过{self.MAX_KEYWORD_LENGTH}个字符"

        if self.SPECIAL_CHAR_PATTERN.search(keyword):
            return False, "关键词不能包含特殊符号"

        return True, ""

    def get_user_keywords(self, user_id: str, active_only: bool = True) -> List[UserKeyword]:
        """获取用户的所有关键词"""
        user_id = str(user_id)  # 确保是字符串
        with get_db_session() as session:
            if active_only:
                results = session.execute(
                    text("""
                        SELECT * FROM user_keywords
                        WHERE user_id = :user_id AND status = 1
                        ORDER BY created_at DESC
                    """),
                    {"user_id": user_id}
                ).fetchall()
            else:
                results = session.execute(
                    text("""
                        SELECT * FROM user_keywords
                        WHERE user_id = :user_id
                        ORDER BY created_at DESC
                    """),
                    {"user_id": user_id}
                ).fetchall()

            return [self._row_to_keyword(row._asdict()) for row in results]

    def get_keyword_by_id(self, keyword_id: int) -> Optional[UserKeyword]:
        """根据ID获取关键词"""
        with get_db_session() as session:
            result = session.execute(
                text("SELECT * FROM user_keywords WHERE id = :id"),
                {"id": keyword_id}
            ).fetchone()

            if not result:
                return None

            return self._row_to_keyword(result._asdict())

    def count_user_keywords(self, user_id: str, active_only: bool = True) -> int:
        """统计用户的关键词数量"""
        user_id = str(user_id)  # 确保是字符串
        with get_db_session() as session:
            if active_only:
                result = session.execute(
                    text("SELECT COUNT(*) FROM user_keywords WHERE user_id = :user_id AND status = 1"),
                    {"user_id": user_id}
                ).fetchone()
            else:
                result = session.execute(
                    text("SELECT COUNT(*) FROM user_keywords WHERE user_id = :user_id"),
                    {"user_id": user_id}
                ).fetchone()
            return result[0] if result else 0

    def keyword_exists(self, user_id: str, keyword: str) -> bool:
        """检查关键词是否已存在（大小写不敏感）"""
        user_id = str(user_id)  # 确保是字符串
        with get_db_session() as session:
            result = session.execute(
                text("""
                    SELECT 1 FROM user_keywords
                    WHERE user_id = :user_id AND LOWER(keyword) = LOWER(:keyword) AND status = 1
                """),
                {"user_id": user_id, "keyword": keyword}
            ).fetchone()
            return result is not None

    def add_keyword(
        self,
        user_id: str,
        keyword: str,
        channel: str = "其他"
    ) -> Tuple[Optional[UserKeyword], str]:
        """
        添加关键词
        返回: (关键词对象, 错误信息)
        """
        user_id = str(user_id)  # 确保是字符串
        keyword = keyword.strip()

        # 验证格式
        valid, error = self.validate_keyword(keyword)
        if not valid:
            return None, error

        # 检查数量上限
        count = self.count_user_keywords(user_id)
        if count >= self.MAX_KEYWORDS_PER_USER:
            return None, f"已达关键词数量上限（{self.MAX_KEYWORDS_PER_USER}个）"

        # 检查是否已存在
        if self.keyword_exists(user_id, keyword):
            return None, f"「{keyword}」已添加，请勿重复添加"

        # 写入数据库
        now = datetime.now()
        with get_db_session() as session:
            result = session.execute(
                text("""
                    INSERT INTO user_keywords (user_id, keyword, channel, status, created_at, updated_at)
                    VALUES (:user_id, :keyword, :channel, 1, :created_at, :updated_at)
                    RETURNING id
                """),
                {
                    "user_id": user_id,
                    "keyword": keyword,
                    "channel": channel,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            keyword_id = result.fetchone()[0]

            return UserKeyword(
                id=keyword_id,
                user_id=user_id,
                keyword=keyword,
                channel=channel,
                status=1,
                created_at=now,
                updated_at=now,
            ), ""

    def delete_keyword(self, user_id: str, keyword_id: int) -> Tuple[bool, str]:
        """
        删除关键词（软删除）
        返回: (是否成功, 错误信息)
        """
        user_id = str(user_id)  # 确保是字符串
        with get_db_session() as session:
            # 检查关键词是否存在且属于该用户
            result = session.execute(
                text("""
                    SELECT id, keyword FROM user_keywords
                    WHERE id = :id AND user_id = :user_id AND status = 1
                """),
                {"id": keyword_id, "user_id": user_id}
            ).fetchone()

            if not result:
                return False, "关键词不存在或已删除"

            keyword = result[1]

            # 软删除关键词
            session.execute(
                text("""
                    UPDATE user_keywords SET status = 0, updated_at = :updated_at
                    WHERE id = :id
                """),
                {"id": keyword_id, "updated_at": datetime.now()}
            )

            # 解除该关键词下的所有订阅关系
            session.execute(
                text("""
                    UPDATE user_video_subscriptions SET status = 0
                    WHERE user_id = :user_id AND keyword = :keyword
                """),
                {"user_id": user_id, "keyword": keyword}
            )

            return True, ""

    def update_keyword_status(
        self,
        keyword_id: int,
        user_id: str,
        status: int
    ) -> Tuple[bool, str]:
        """
        更新关键词状态
        返回: (是否成功, 错误信息)
        """
        user_id = str(user_id)  # 确保是字符串
        with get_db_session() as session:
            result = session.execute(
                text("""
                    UPDATE user_keywords SET status = :status, updated_at = :updated_at
                    WHERE id = :id AND user_id = :user_id
                    RETURNING id
                """),
                {"id": keyword_id, "user_id": user_id, "status": status, "updated_at": datetime.now()}
            )

            if result.rowcount == 0:
                return False, "关键词不存在"

            return True, ""

    def get_all_active_keywords(self) -> List[str]:
        """获取所有活跃关键词（去重）"""
        with get_db_session() as session:
            results = session.execute(
                text("""
                    SELECT DISTINCT keyword FROM user_keywords
                    WHERE status = 1
                """)
            ).fetchall()
            return [row[0] for row in results]

    def _row_to_keyword(self, row: dict) -> UserKeyword:
        """将数据库行转换为UserKeyword对象"""
        return UserKeyword(
            id=row.get("id"),
            user_id=row.get("user_id", ""),
            keyword=row.get("keyword", ""),
            channel=row.get("channel", "其他"),
            status=row.get("status", 1),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )
