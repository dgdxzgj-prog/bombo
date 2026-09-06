"""
用户订阅Feed服务
"""
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy import text

from src.models.user_video_subscription import UserVideoSubscription
from src.models.user_monitor_video import UserMonitorVideo, UserVideoStatus
from src.utils.database import get_db_session


class UserFeedService:
    """用户订阅Feed服务类"""

    def get_user_feed(
        self,
        user_id: str,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        channel: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "max_online_today",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取用户订阅的视频列表

        Args:
            user_id: 用户ID
            status: 视频状态过滤
            keyword: 关键词过滤
            channel: 赛道过滤
            search: 搜索（标题或作者）
            sort_by: 排序字段
            sort_order: 排序方向 (asc/desc)
            limit: 返回数量
            offset: 偏移量

        Returns:
            视频列表（包含视频信息和订阅信息）
        """
        user_id = str(user_id)  # 确保是字符串
        # 构建查询
        query = """
            SELECT
                ump.*,
                uvs.keyword as subscribed_keyword,
                uvs.subscribed_at
            FROM user_video_subscriptions uvs
            JOIN user_monitor_pool ump ON uvs.bvid = ump.bvid
            WHERE uvs.user_id = :user_id
              AND uvs.status = 1
        """
        params: Dict[str, Any] = {"user_id": user_id}

        if status:
            query += " AND ump.status = :status"
            params["status"] = status

        if keyword:
            query += " AND ump.keyword = :keyword"
            params["keyword"] = keyword

        if channel:
            query += " AND ump.channel = :channel"
            params["channel"] = channel

        if search:
            query += " AND (ump.title LIKE :search OR ump.author LIKE :search)"
            params["search"] = f"%{search}%"

        # 排序
        valid_sort_fields = ["max_online_today", "view_today", "growth_rate", "first_seen", "subscribed_at"]
        if sort_by not in valid_sort_fields:
            sort_by = "max_online_today"

        sort_order = "DESC" if sort_order.lower() == "desc" else "ASC"
        query += f" ORDER BY ump.{sort_by} {sort_order}"

        query += " LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset

        with get_db_session() as session:
            results = session.execute(text(query), params).fetchall()

            feeds = []
            for row in results:
                feed = row._asdict()
                # 转换状态
                status_val = feed.get("status", "monitoring")
                if isinstance(status_val, str):
                    feed["status"] = UserVideoStatus(status_val)
                feeds.append(feed)

            return feeds

    def get_user_feed_count(
        self,
        user_id: str,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        channel: Optional[str] = None,
        search: Optional[str] = None
    ) -> int:
        """获取用户订阅的视频总数"""
        user_id = str(user_id)  # 确保是字符串
        query = """
            SELECT COUNT(*)
            FROM user_video_subscriptions uvs
            JOIN user_monitor_pool ump ON uvs.bvid = ump.bvid
            WHERE uvs.user_id = :user_id
              AND uvs.status = 1
        """
        params: Dict[str, Any] = {"user_id": user_id}

        if status:
            query += " AND ump.status = :status"
            params["status"] = status

        if keyword:
            query += " AND ump.keyword = :keyword"
            params["keyword"] = keyword

        if channel:
            query += " AND ump.channel = :channel"
            params["channel"] = channel

        if search:
            query += " AND (ump.title LIKE :search OR ump.author LIKE :search)"
            params["search"] = f"%{search}%"

        with get_db_session() as session:
            result = session.execute(text(query), params).fetchone()
            return result[0] if result else 0

    def get_feed_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户订阅统计信息"""
        user_id = str(user_id)  # 确保是字符串
        with get_db_session() as session:
            # 总视频数
            total_result = session.execute(
                text("""
                    SELECT COUNT(*)
                    FROM user_video_subscriptions
                    WHERE user_id = :user_id AND status = 1
                """),
                {"user_id": user_id}
            ).fetchone()
            total = total_result[0] if total_result else 0

            # 各状态数量
            status_result = session.execute(
                text("""
                    SELECT ump.status, COUNT(*)
                    FROM user_video_subscriptions uvs
                    JOIN user_monitor_pool ump ON uvs.bvid = ump.bvid
                    WHERE uvs.user_id = :user_id AND uvs.status = 1
                    GROUP BY ump.status
                """),
                {"user_id": user_id}
            ).fetchall()

            status_counts = {"monitoring": 0, "featured": 0, "declined": 0}
            for row in status_result:
                status_counts[row[0]] = row[1]

            # 各赛道数量
            channel_result = session.execute(
                text("""
                    SELECT ump.channel, COUNT(*)
                    FROM user_video_subscriptions uvs
                    JOIN user_monitor_pool ump ON uvs.bvid = ump.bvid
                    WHERE uvs.user_id = :user_id AND uvs.status = 1
                    GROUP BY ump.channel
                    ORDER BY COUNT(*) DESC
                    LIMIT 10
                """),
                {"user_id": user_id}
            ).fetchall()

            channel_counts = [{"channel": row[0], "count": row[1]} for row in channel_result]

            # 各关键词数量
            keyword_result = session.execute(
                text("""
                    SELECT uvs.keyword, COUNT(*)
                    FROM user_video_subscriptions uvs
                    WHERE uvs.user_id = :user_id AND uvs.status = 1
                    GROUP BY uvs.keyword
                    ORDER BY COUNT(*) DESC
                """),
                {"user_id": user_id}
            ).fetchall()

            keyword_counts = [{"keyword": row[0], "count": row[1]} for row in keyword_result]

            return {
                "total": total,
                "status_counts": status_counts,
                "channel_counts": channel_counts,
                "keyword_counts": keyword_counts,
            }

    def subscribe_video(
        self,
        user_id: str,
        bvid: str,
        keyword: str
    ) -> Tuple[bool, str]:
        """
        订阅视频
        返回: (是否成功, 错误信息)
        """
        user_id = str(user_id)  # 确保是字符串
        with get_db_session() as session:
            # 检查是否已订阅
            result = session.execute(
                text("""
                    SELECT id FROM user_video_subscriptions
                    WHERE user_id = :user_id AND bvid = :bvid
                """),
                {"user_id": user_id, "bvid": bvid}
            ).fetchone()

            if result:
                # 已订阅，更新为活跃状态
                session.execute(
                    text("""
                        UPDATE user_video_subscriptions
                        SET status = 1, keyword = :keyword
                        WHERE user_id = :user_id AND bvid = :bvid
                    """),
                    {"user_id": user_id, "bvid": bvid, "keyword": keyword}
                )
            else:
                # 新订阅
                session.execute(
                    text("""
                        INSERT INTO user_video_subscriptions (user_id, bvid, keyword, subscribed_at, status)
                        VALUES (:user_id, :bvid, :keyword, :subscribed_at, 1)
                    """),
                    {
                        "user_id": user_id,
                        "bvid": bvid,
                        "keyword": keyword,
                        "subscribed_at": datetime.now(),
                    }
                )

            return True, ""

    def unsubscribe_video(self, user_id: str, bvid: str) -> bool:
        """取消订阅视频"""
        user_id = str(user_id)  # 确保是字符串
        with get_db_session() as session:
            result = session.execute(
                text("""
                    UPDATE user_video_subscriptions
                    SET status = 0
                    WHERE user_id = :user_id AND bvid = :bvid
                """),
                {"user_id": user_id, "bvid": bvid}
            )
            return result.rowcount > 0

    def unsubscribe_by_keyword(self, user_id: str, keyword: str) -> int:
        """取消关键词下的所有订阅"""
        user_id = str(user_id)  # 确保是字符串
        with get_db_session() as session:
            result = session.execute(
                text("""
                    UPDATE user_video_subscriptions
                    SET status = 0
                    WHERE user_id = :user_id AND keyword = :keyword
                """),
                {"user_id": user_id, "keyword": keyword}
            )
            return result.rowcount

    def batch_subscribe_videos(
        self,
        user_id: str,
        bvids: List[str],
        keyword: str
    ) -> int:
        """
        批量订阅视频
        返回: 成功订阅的数量
        """
        user_id = str(user_id)  # 确保是字符串
        if not bvids:
            return 0

        now = datetime.now()
        subscribed_count = 0

        with get_db_session() as session:
            for bvid in bvids:
                # 检查是否已存在
                exists = session.execute(
                    text("""
                        SELECT id FROM user_video_subscriptions
                        WHERE user_id = :user_id AND bvid = :bvid
                    """),
                    {"user_id": user_id, "bvid": bvid}
                ).fetchone()

                if exists:
                    # 更新为活跃状态
                    session.execute(
                        text("""
                            UPDATE user_video_subscriptions
                            SET status = 1, keyword = :keyword
                            WHERE user_id = :user_id AND bvid = :bvid
                        """),
                        {"user_id": user_id, "bvid": bvid, "keyword": keyword}
                    )
                else:
                    # 新增
                    session.execute(
                        text("""
                            INSERT INTO user_video_subscriptions (user_id, bvid, keyword, subscribed_at, status)
                            VALUES (:user_id, :bvid, :keyword, :subscribed_at, 1)
                        """),
                        {
                            "user_id": user_id,
                            "bvid": bvid,
                            "keyword": keyword,
                            "subscribed_at": now,
                        }
                    )
                subscribed_count += 1

            return subscribed_count

    def get_user_categories(self, user_id: str) -> List[str]:
        """获取用户订阅视频涉及的所有赛道"""
        user_id = str(user_id)  # 确保是字符串
        with get_db_session() as session:
            results = session.execute(
                text("""
                    SELECT DISTINCT ump.channel
                    FROM user_video_subscriptions uvs
                    JOIN user_monitor_pool ump ON uvs.bvid = ump.bvid
                    WHERE uvs.user_id = :user_id AND uvs.status = 1
                    ORDER BY ump.channel
                """),
                {"user_id": user_id}
            ).fetchall()
            return [row[0] for row in results]

    def get_user_keywords_with_counts(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户关键词列表（带视频数量）"""
        user_id = str(user_id)  # 确保是字符串
        with get_db_session() as session:
            results = session.execute(
                text("""
                    SELECT
                        uk.id,
                        uk.keyword,
                        uk.channel,
                        uk.status,
                        uk.created_at,
                        COUNT(CASE WHEN ump.status != 'declined' AND uvs.status = 1 THEN 1 END) as video_count
                    FROM user_keywords uk
                    LEFT JOIN user_video_subscriptions uvs ON uk.keyword = uvs.keyword AND uvs.user_id = uk.user_id
                    LEFT JOIN user_monitor_pool ump ON uvs.bvid = ump.bvid
                    WHERE uk.user_id = :user_id
                    GROUP BY uk.id, uk.keyword, uk.channel, uk.status, uk.created_at
                    ORDER BY uk.created_at DESC
                """),
                {"user_id": user_id}
            ).fetchall()

            return [
                {
                    "id": row[0],
                    "keyword": row[1],
                    "channel": row[2],
                    "status": row[3],
                    "created_at": row[4],
                    "video_count": row[5],
                }
                for row in results
            ]

    def ensure_video_keywords_table(self) -> None:
        """确保 video_keywords 表存在"""
        with get_db_session() as session:
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS video_keywords (
                    id SERIAL PRIMARY KEY,
                    bvid VARCHAR(20) NOT NULL,
                    keyword VARCHAR(50) NOT NULL,
                    user_id VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(bvid, keyword, user_id)
                )
            """))
            # 创建索引加速查询
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_video_keywords_bvid ON video_keywords(bvid)
            """))
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_video_keywords_keyword ON video_keywords(keyword)
            """))

    def add_video_keyword(self, bvid: str, keyword: str, user_id: str) -> bool:
        """
        添加视频-关键词关联
        如果已存在则忽略
        返回: 是否新增成功
        """
        with get_db_session() as session:
            result = session.execute(
                text("""
                    INSERT INTO video_keywords (bvid, keyword, user_id, created_at)
                    VALUES (:bvid, :keyword, :user_id, :created_at)
                    ON CONFLICT (bvid, keyword, user_id) DO NOTHING
                    RETURNING id
                """),
                {"bvid": bvid, "keyword": keyword, "user_id": str(user_id), "created_at": datetime.now()}
            )
            return result.fetchone() is not None

    def batch_add_video_keywords(self, bvid: str, keyword: str, user_ids: List[str]) -> int:
        """
        批量添加视频-关键词关联（为多个用户）
        返回: 新增数量
        """
        if not user_ids:
            return 0

        added_count = 0
        with get_db_session() as session:
            for user_id in user_ids:
                result = session.execute(
                    text("""
                        INSERT INTO video_keywords (bvid, keyword, user_id, created_at)
                        VALUES (:bvid, :keyword, :user_id, :created_at)
                        ON CONFLICT (bvid, keyword, user_id) DO NOTHING
                        RETURNING id
                    """),
                    {"bvid": bvid, "keyword": keyword, "user_id": str(user_id), "created_at": datetime.now()}
                )
                if result.fetchone():
                    added_count += 1
            return added_count

    def batch_subscribe_videos_for_users(
        self,
        bvid: str,
        keyword: str,
        user_ids: List[str]
    ) -> int:
        """
        为多个用户批量订阅同一个视频
        返回: 订阅成功数量
        """
        if not user_ids:
            return 0

        now = datetime.now()
        subscribed_count = 0

        with get_db_session() as session:
            for user_id in user_ids:
                # 检查是否已存在
                exists = session.execute(
                    text("""
                        SELECT id FROM user_video_subscriptions
                        WHERE user_id = :user_id AND bvid = :bvid
                    """),
                    {"user_id": str(user_id), "bvid": bvid}
                ).fetchone()

                if exists:
                    # 更新为活跃状态
                    session.execute(
                        text("""
                            UPDATE user_video_subscriptions
                            SET status = 1, keyword = :keyword
                            WHERE user_id = :user_id AND bvid = :bvid
                        """),
                        {"user_id": str(user_id), "bvid": bvid, "keyword": keyword}
                    )
                else:
                    # 新增
                    session.execute(
                        text("""
                            INSERT INTO user_video_subscriptions (user_id, bvid, keyword, subscribed_at, status)
                            VALUES (:user_id, :bvid, :keyword, :subscribed_at, 1)
                        """),
                        {
                            "user_id": str(user_id),
                            "bvid": bvid,
                            "keyword": keyword,
                            "subscribed_at": now,
                        }
                    )
                subscribed_count += 1

            return subscribed_count


# 需要 Tuple
from typing import Tuple
