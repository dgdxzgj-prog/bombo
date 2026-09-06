"""
用户自选赛道监控池服务
"""
import json
from datetime import datetime
from typing import List, Optional, Generator, Dict, Any

from sqlalchemy import text

from src.models.user_monitor_video import UserMonitorVideo, UserVideoStatus
from src.utils.database import get_db_session


class UserMonitorService:
    """用户自选赛道监控池服务类"""

    def add_video(self, video: UserMonitorVideo) -> UserMonitorVideo:
        """
        添加视频到用户监控池
        如果bvid已存在则更新，否则插入
        """
        with get_db_session() as session:
            now = datetime.now()

            # 检查是否已存在
            result = session.execute(
                text("SELECT id FROM user_monitor_pool WHERE bvid = :bvid"),
                {"bvid": video.bvid}
            ).fetchone()

            if result:
                # 已存在，更新数据
                session.execute(
                    text("""
                        UPDATE user_monitor_pool SET
                            title = :title,
                            author = :author,
                            author_mid = :author_mid,
                            channel = :channel,
                            keyword = :keyword,
                            view_yesterday = :view_yesterday,
                            view_today = :view_today,
                            growth_rate = :growth_rate,
                            like_count = :like_count,
                            favorite_count = :favorite_count,
                            reply_count = :reply_count,
                            coin_count = :coin_count,
                            share_count = :share_count,
                            danmu_count = :danmu_count,
                            online_count = :online_count,
                            max_online_today = :max_online_today,
                            pubdate = :pubdate,
                            cover_url = :cover_url,
                            duration = :duration,
                            tags = :tags,
                            status = :status,
                            last_collected = :last_collected,
                            updated_at = :updated_at
                        WHERE bvid = :bvid
                    """),
                    {
                        "bvid": video.bvid,
                        "title": video.title,
                        "author": video.author,
                        "author_mid": video.author_mid,
                        "channel": video.channel,
                        "keyword": video.keyword,
                        "view_yesterday": video.view_yesterday,
                        "view_today": video.view_today,
                        "growth_rate": video.growth_rate,
                        "like_count": video.like_count,
                        "favorite_count": video.favorite_count,
                        "reply_count": video.reply_count,
                        "coin_count": video.coin_count,
                        "share_count": video.share_count,
                        "danmu_count": video.danmu_count,
                        "online_count": video.online_count,
                        "max_online_today": video.max_online_today,
                        "pubdate": video.pubdate,
                        "cover_url": video.cover_url,
                        "duration": video.duration or 0,
                        "tags": json.dumps(video.tags) if video.tags else None,
                        "status": video.status.value if isinstance(video.status, UserVideoStatus) else video.status,
                        "last_collected": now,
                        "updated_at": now,
                    }
                )
                video.id = result[0]
            else:
                # 不存在，插入新记录
                result = session.execute(
                    text("""
                        INSERT INTO user_monitor_pool
                        (bvid, title, author, author_mid, channel, keyword, view_yesterday, view_today,
                         growth_rate, like_count, favorite_count, reply_count, coin_count, share_count,
                         danmu_count, online_count, max_online_today, pubdate, cover_url, duration, tags,
                         status, first_seen, last_collected, created_at, updated_at)
                        VALUES
                        (:bvid, :title, :author, :author_mid, :channel, :keyword, :view_yesterday, :view_today,
                         :growth_rate, :like_count, :favorite_count, :reply_count, :coin_count, :share_count,
                         :danmu_count, :online_count, :max_online_today, :pubdate, :cover_url, :duration, :tags,
                         :status, :first_seen, :last_collected, :created_at, :updated_at)
                        RETURNING id
                    """),
                    {
                        "bvid": video.bvid,
                        "title": video.title,
                        "author": video.author,
                        "author_mid": video.author_mid,
                        "channel": video.channel,
                        "keyword": video.keyword,
                        "view_yesterday": video.view_yesterday,
                        "view_today": video.view_today,
                        "growth_rate": video.growth_rate,
                        "like_count": video.like_count,
                        "favorite_count": video.favorite_count,
                        "reply_count": video.reply_count,
                        "coin_count": video.coin_count,
                        "share_count": video.share_count,
                        "danmu_count": video.danmu_count,
                        "online_count": video.online_count,
                        "max_online_today": video.max_online_today,
                        "pubdate": video.pubdate,
                        "cover_url": video.cover_url,
                        "duration": video.duration or 0,
                        "tags": json.dumps(video.tags) if video.tags else None,
                        "status": video.status.value if isinstance(video.status, UserVideoStatus) else video.status,
                        "first_seen": now,
                        "last_collected": now,
                        "created_at": now,
                        "updated_at": now,
                    }
                )
                video.id = result.fetchone()[0]

            return video

    def get_video_by_bvid(self, bvid: str) -> Optional[UserMonitorVideo]:
        """根据bvid获取视频"""
        with get_db_session() as session:
            result = session.execute(
                text("SELECT * FROM user_monitor_pool WHERE bvid = :bvid"),
                {"bvid": bvid}
            ).fetchone()

            if not result:
                return None

            row = result._asdict()
            return self._row_to_video(row)

    def video_exists(self, bvid: str) -> bool:
        """检查视频是否存在"""
        with get_db_session() as session:
            result = session.execute(
                text("SELECT 1 FROM user_monitor_pool WHERE bvid = :bvid"),
                {"bvid": bvid}
            ).fetchone()
            return result is not None

    def iter_videos_by_status(
        self,
        status: str,
        limit: int = 1000,
        batch_size: int = 100
    ) -> Generator[UserMonitorVideo, None, None]:
        """按状态迭代视频（流式）"""
        offset = 0
        while True:
            with get_db_session() as session:
                results = session.execute(
                    text("""
                        SELECT * FROM user_monitor_pool
                        WHERE status = :status
                        ORDER BY id
                        LIMIT :limit OFFSET :offset
                    """),
                    {"status": status, "limit": batch_size, "offset": offset}
                ).fetchall()

                if not results:
                    break

                for row in results:
                    yield self._row_to_video(row._asdict())

                if len(results) < batch_size:
                    break

                offset += batch_size
                if offset >= limit:
                    break

    def iter_videos_by_keyword(
        self,
        keyword: str,
        limit: int = 1000,
        batch_size: int = 100
    ) -> Generator[UserMonitorVideo, None, None]:
        """按关键词迭代视频（流式）"""
        offset = 0
        while True:
            with get_db_session() as session:
                results = session.execute(
                    text("""
                        SELECT * FROM user_monitor_pool
                        WHERE keyword = :keyword
                        ORDER BY id
                        LIMIT :limit OFFSET :offset
                    """),
                    {"keyword": keyword, "limit": batch_size, "offset": offset}
                ).fetchall()

                if not results:
                    break

                for row in results:
                    yield self._row_to_video(row._asdict())

                if len(results) < batch_size:
                    break

                offset += batch_size
                if offset >= limit:
                    break

    def iter_all_monitoring_videos(
        self,
        limit: int = 10000,
        batch_size: int = 100
    ) -> Generator[UserMonitorVideo, None, None]:
        """迭代所有监控中的视频（流式）"""
        offset = 0
        while True:
            with get_db_session() as session:
                results = session.execute(
                    text("""
                        SELECT * FROM user_monitor_pool
                        WHERE status IN ('monitoring', 'featured')
                        ORDER BY id
                        LIMIT :limit OFFSET :offset
                    """),
                    {"limit": batch_size, "offset": offset}
                ).fetchall()

                if not results:
                    break

                for row in results:
                    yield self._row_to_video(row._asdict())

                if len(results) < batch_size:
                    break

                offset += batch_size
                if offset >= limit:
                    break

    def update_video_stats(
        self,
        bvid: str,
        view_today: int,
        like_count: int = 0,
        favorite_count: int = 0,
        reply_count: int = 0,
        coin_count: int = 0,
        share_count: int = 0,
        danmu_count: int = 0,
        online_count: int = 0
    ) -> bool:
        """更新视频统计数据"""
        with get_db_session() as session:
            # 获取当前的view_yesterday和view_today
            result = session.execute(
                text("SELECT view_yesterday, view_today FROM user_monitor_pool WHERE bvid = :bvid"),
                {"bvid": bvid}
            ).fetchone()

            if not result:
                return False

            view_yesterday = result[0]
            view_today_old = result[1]

            # 计算增速
            growth_rate = 0.0
            if view_yesterday > 0:
                growth_rate = round((view_today - view_yesterday) / view_yesterday * 100, 4)

            now = datetime.now()
            session.execute(
                text("""
                    UPDATE user_monitor_pool SET
                        view_yesterday = :view_yesterday,
                        view_today = :view_today,
                        growth_rate = :growth_rate,
                        like_count = :like_count,
                        favorite_count = :favorite_count,
                        reply_count = :reply_count,
                        coin_count = :coin_count,
                        share_count = :share_count,
                        danmu_count = :danmu_count,
                        online_count = :online_count,
                        last_collected = :last_collected,
                        updated_at = :updated_at
                    WHERE bvid = :bvid
                """),
                {
                    "bvid": bvid,
                    "view_yesterday": view_today_old,
                    "view_today": view_today,
                    "growth_rate": growth_rate,
                    "like_count": like_count,
                    "favorite_count": favorite_count,
                    "reply_count": reply_count,
                    "coin_count": coin_count,
                    "share_count": share_count,
                    "danmu_count": danmu_count,
                    "online_count": online_count,
                    "last_collected": now,
                    "updated_at": now,
                }
            )
            return True

    def update_max_online_today(self, bvid: str, online_count: int) -> bool:
        """更新当日最大在线人数（只增不减）"""
        with get_db_session() as session:
            result = session.execute(
                text("""
                    UPDATE user_monitor_pool
                    SET max_online_today = GREATEST(max_online_today, :online_count),
                        updated_at = :updated_at
                    WHERE bvid = :bvid
                """),
                {"bvid": bvid, "online_count": online_count, "updated_at": datetime.now()}
            )
            return result.rowcount > 0

    def update_video_status(
        self,
        bvid: str,
        status: UserVideoStatus,
        featured_at: Optional[datetime] = None,
        declined_at: Optional[datetime] = None,
        declined_reason: Optional[str] = None
    ) -> bool:
        """更新视频状态"""
        with get_db_session() as session:
            now = datetime.now()

            # 构建更新字段
            update_fields = "status = :status, updated_at = :updated_at"
            params = {
                "bvid": bvid,
                "status": status.value if isinstance(status, UserVideoStatus) else status,
                "updated_at": now,
            }

            if featured_at:
                update_fields += ", featured_at = :featured_at"
                params["featured_at"] = featured_at

            if declined_at:
                update_fields += ", declined_at = :declined_at"
                params["declined_at"] = declined_at

            if declined_reason:
                update_fields += ", declined_reason = :declined_reason"
                params["declined_reason"] = declined_reason

            result = session.execute(
                text(f"UPDATE user_monitor_pool SET {update_fields} WHERE bvid = :bvid"),
                params
            )
            return result.rowcount > 0

    def batch_update_declined(self, bvids: List[str], reason: str) -> int:
        """批量标记视频为衰退"""
        if not bvids:
            return 0

        now = datetime.now()
        with get_db_session() as session:
            result = session.execute(
                text("""
                    UPDATE user_monitor_pool SET
                        status = 'declined',
                        declined_at = :declined_at,
                        declined_reason = :reason,
                        updated_at = :updated_at
                    WHERE bvid = ANY(:bvids) AND status = 'monitoring'
                """),
                {"bvids": bvids, "declined_at": now, "reason": reason, "updated_at": now}
            )
            return result.rowcount

    def reset_daily_max_online(self) -> int:
        """重置每日最大在线人数"""
        with get_db_session() as session:
            result = session.execute(
                text("UPDATE user_monitor_pool SET max_online_today = 0 WHERE max_online_today > 0")
            )
            return result.rowcount

    def get_videos_by_keyword_and_status(
        self,
        keyword: str,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[UserMonitorVideo]:
        """获取指定关键词和状态的视频列表"""
        with get_db_session() as session:
            if status:
                results = session.execute(
                    text("""
                        SELECT * FROM user_monitor_pool
                        WHERE keyword = :keyword AND status = :status
                        ORDER BY max_online_today DESC
                        LIMIT :limit OFFSET :offset
                    """),
                    {"keyword": keyword, "status": status, "limit": limit, "offset": offset}
                ).fetchall()
            else:
                results = session.execute(
                    text("""
                        SELECT * FROM user_monitor_pool
                        WHERE keyword = :keyword
                        ORDER BY max_online_today DESC
                        LIMIT :limit OFFSET :offset
                    """),
                    {"keyword": keyword, "limit": limit, "offset": offset}
                ).fetchall()

            return [self._row_to_video(row._asdict()) for row in results]

    def count_videos_by_keyword(self, keyword: str, include_declined: bool = False) -> int:
        """统计关键词下的视频数量"""
        with get_db_session() as session:
            if include_declined:
                result = session.execute(
                    text("SELECT COUNT(*) FROM user_monitor_pool WHERE keyword = :keyword"),
                    {"keyword": keyword}
                ).fetchone()
            else:
                result = session.execute(
                    text("SELECT COUNT(*) FROM user_monitor_pool WHERE keyword = :keyword AND status != 'declined'"),
                    {"keyword": keyword}
                ).fetchone()
            return result[0] if result else 0

    def count_videos_by_status(self, status: str) -> int:
        """按状态统计视频数量"""
        with get_db_session() as session:
            result = session.execute(
                text("SELECT COUNT(*) FROM user_monitor_pool WHERE status = :status"),
                {"status": status}
            ).fetchone()
            return result[0] if result else 0

    def _row_to_video(self, row: Dict[str, Any]) -> UserMonitorVideo:
        """将数据库行转换为UserMonitorVideo对象"""
        tags = row.get("tags")
        if tags and isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except json.JSONDecodeError:
                tags = None

        status = row.get("status", "monitoring")
        if isinstance(status, str):
            status = UserVideoStatus(status)

        pubdate = row.get("pubdate")
        first_seen = row.get("first_seen")
        last_collected = row.get("last_collected")
        featured_at = row.get("featured_at")
        declined_at = row.get("declined_at")
        created_at = row.get("created_at")
        updated_at = row.get("updated_at")

        return UserMonitorVideo(
            id=row.get("id"),
            bvid=row.get("bvid", ""),
            title=row.get("title", ""),
            author=row.get("author", ""),
            author_mid=row.get("author_mid"),
            channel=row.get("channel", "其他"),
            keyword=row.get("keyword", ""),
            view_yesterday=row.get("view_yesterday", 0),
            view_today=row.get("view_today", 0),
            growth_rate=float(row.get("growth_rate", 0) or 0),
            like_count=row.get("like_count", 0),
            favorite_count=row.get("favorite_count", 0),
            reply_count=row.get("reply_count", 0),
            coin_count=row.get("coin_count", 0),
            share_count=row.get("share_count", 0),
            danmu_count=row.get("danmu_count", 0),
            online_count=row.get("online_count", 0),
            max_online_today=row.get("max_online_today", 0),
            pubdate=pubdate,
            cover_url=row.get("cover_url"),
            duration=row.get("duration", 0),
            tags=tags,
            status=status,
            first_seen=first_seen,
            last_collected=last_collected,
            featured_at=featured_at,
            declined_at=declined_at,
            declined_reason=row.get("declined_reason"),
            created_at=created_at,
            updated_at=updated_at,
        )
