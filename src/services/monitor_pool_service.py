"""
监控池服务层
"""
from datetime import datetime
from typing import List, Optional, Generator

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.models.video import Video, VideoStatus
from src.utils.database import get_db_session


class MonitorPoolService:
    """监控池服务类"""

    def add_video(self, video: Video) -> Video:
        """
        添加视频到监控池
        如果bvid已存在则抛出异常
        """
        with get_db_session() as session:
            # 检查是否已存在
            result = session.execute(
                text("SELECT id FROM monitor_pool WHERE bvid = :bvid"),
                {"bvid": video.bvid}
            ).fetchone()

            if result:
                raise ValueError(f"Video with bvid {video.bvid} already exists")

            now = datetime.now()
            result = session.execute(
                text("""
                    INSERT INTO monitor_pool
                    (bvid, title, author, channel, keyword, view_yesterday, view_today,
                     growth_rate, like_count, favorite_count, reply_count, pubdate,
                     cover_url, status, first_seen, last_collected, created_at, updated_at)
                    VALUES
                    (:bvid, :title, :author, :channel, :keyword, :view_yesterday, :view_today,
                     :growth_rate, :like_count, :favorite_count, :reply_count, :pubdate,
                     :cover_url, :status, :first_seen, :last_collected, :created_at, :updated_at)
                    RETURNING id
                """),
                {
                    "bvid": video.bvid,
                    "title": video.title,
                    "author": video.author,
                    "channel": video.channel,
                    "keyword": video.keyword,
                    "view_yesterday": video.view_yesterday,
                    "view_today": video.view_today,
                    "growth_rate": video.growth_rate,
                    "like_count": video.like_count,
                    "favorite_count": video.favorite_count,
                    "reply_count": video.reply_count,
                    "pubdate": video.pubdate,
                    "cover_url": video.cover_url,
                    "status": video.status.value if isinstance(video.status, VideoStatus) else video.status,
                    "first_seen": video.first_seen or now,
                    "last_collected": video.last_collected,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            video.id = result.fetchone()[0]
            return video

    def get_video_by_bvid(self, bvid: str) -> Optional[Video]:
        """根据bvid获取视频"""
        with get_db_session() as session:
            result = session.execute(
                text("""
                    SELECT id, bvid, title, author, channel, keyword,
                           view_yesterday, view_today, growth_rate,
                           like_count, favorite_count, reply_count,
                           pubdate, cover_url, status,
                           first_seen, last_collected, created_at, updated_at
                    FROM monitor_pool WHERE bvid = :bvid
                """),
                {"bvid": bvid}
            ).fetchone()

            if result is None:
                return None

            return Video(
                id=result[0],
                bvid=result[1],
                title=result[2] or "",
                author=result[3] or "",
                channel=result[4] or "",
                keyword=result[5] or "",
                view_yesterday=result[6] or 0,
                view_today=result[7] or 0,
                growth_rate=float(result[8] or 0),
                like_count=result[9] or 0,
                favorite_count=result[10] or 0,
                reply_count=result[11] or 0,
                pubdate=result[12],
                cover_url=result[13],
                status=VideoStatus(result[14]) if result[14] else VideoStatus.MONITORING,
                first_seen=result[15],
                last_collected=result[16],
                created_at=result[17],
                updated_at=result[18],
            )

    def get_videos_by_channel(self, channel: str, limit: int = 100) -> List[Video]:
        """根据赛道获取视频列表"""
        with get_db_session() as session:
            results = session.execute(
                text("""
                    SELECT id, bvid, title, author, channel, keyword,
                           view_yesterday, view_today, growth_rate,
                           like_count, favorite_count, reply_count,
                           pubdate, cover_url, status,
                           first_seen, last_collected, created_at, updated_at
                    FROM monitor_pool
                    WHERE channel = :channel
                    ORDER BY growth_rate DESC
                    LIMIT :limit
                """),
                {"channel": channel, "limit": limit}
            ).fetchall()

            return [self._row_to_video(row) for row in results]

    def get_videos_by_status(
        self,
        status: VideoStatus,
        limit: int = 100,
        offset: int = 0
    ) -> List[Video]:
        """根据状态获取视频列表"""
        with get_db_session() as session:
            results = session.execute(
                text("""
                    SELECT id, bvid, title, author, channel, keyword,
                           view_yesterday, view_today, growth_rate,
                           like_count, favorite_count, reply_count,
                           pubdate, cover_url, status,
                           first_seen, last_collected, created_at, updated_at
                    FROM monitor_pool
                    WHERE status = :status
                    ORDER BY growth_rate DESC
                    LIMIT :limit OFFSET :offset
                """),
                {"status": status.value, "limit": limit, "offset": offset}
            ).fetchall()

            return [self._row_to_video(row) for row in results]

    def get_videos_by_status_and_channel(
        self,
        status: VideoStatus,
        channel: str,
        limit: int = 100,
    ) -> List[Video]:
        """根据状态和赛道获取视频列表"""
        with get_db_session() as session:
            results = session.execute(
                text("""
                    SELECT id, bvid, title, author, channel, keyword,
                           view_yesterday, view_today, growth_rate,
                           like_count, favorite_count, reply_count,
                           pubdate, cover_url, status,
                           first_seen, last_collected, created_at, updated_at
                    FROM monitor_pool
                    WHERE status = :status AND channel = :channel
                    ORDER BY view_today DESC
                    LIMIT :limit
                """),
                {"status": status.value, "channel": channel, "limit": limit}
            ).fetchall()

            return [self._row_to_video(row) for row in results]

    def get_featured_videos_by_channel(
        self,
        channel: str,
        limit: int = 100,
    ) -> List[Video]:
        """获取指定赛道的已上榜视频（按在线人数降序）"""
        with get_db_session() as session:
            results = session.execute(
                text("""
                    SELECT mp.id, mp.bvid, mp.title, mp.author, mp.channel, mp.keyword,
                           mp.view_yesterday, mp.view_today, mp.growth_rate,
                           mp.like_count, mp.favorite_count, mp.reply_count,
                           mp.pubdate, mp.cover_url, mp.status,
                           mp.first_seen, mp.last_collected, mp.created_at, mp.updated_at,
                           COALESCE(hs.online_count, 0) as online_count
                    FROM monitor_pool mp
                    LEFT JOIN (
                        SELECT bvid, online_count
                        FROM hourly_snapshot hs1
                        WHERE snapshot_time = (
                            SELECT MAX(snapshot_time) FROM hourly_snapshot hs2 WHERE hs2.bvid = hs1.bvid
                        )
                    ) hs ON mp.bvid = hs.bvid
                    WHERE mp.status = 'featured' AND (:channel = '' OR mp.channel = :channel)
                    ORDER BY online_count DESC
                    LIMIT :limit
                """),
                {"channel": channel, "limit": limit}
            ).fetchall()

            return [self._row_to_video_with_online(row) for row in results]

    def get_all_monitoring_videos(self) -> List[Video]:
        """获取所有监控中的视频"""
        return self.get_videos_by_status(VideoStatus.MONITORING, limit=100000)

    def iter_videos_by_status(
        self,
        status: VideoStatus,
        batch_size: int = 500,
    ) -> Generator[Video, None, None]:
        """
        分批迭代获取指定状态的视频（生成器模式，避免内存超限）

        Args:
            status: 视频状态
            batch_size: 每批获取数量

        Yields:
            Video 对象
        """
        offset = 0
        while True:
            with get_db_session() as session:
                results = session.execute(
                    text("""
                        SELECT id, bvid, title, author, channel, keyword,
                               view_yesterday, view_today, growth_rate,
                               like_count, favorite_count, reply_count,
                               pubdate, cover_url, status,
                               first_seen, last_collected, created_at, updated_at
                        FROM monitor_pool
                        WHERE status = :status
                        ORDER BY id
                        LIMIT :limit OFFSET :offset
                    """),
                    {"status": status.value, "limit": batch_size, "offset": offset}
                ).fetchall()

                if not results:
                    break

                for row in results:
                    yield self._row_to_video(row)

                if len(results) < batch_size:
                    break

                offset += batch_size

    def iter_all_monitoring_videos(self, batch_size: int = 500) -> Generator[Video, None, None]:
        """
        分批迭代获取所有监控中的视频（生成器模式，避免内存超限）

        Args:
            batch_size: 每批获取数量

        Yields:
            Video 对象
        """
        yield from self.iter_videos_by_status(VideoStatus.MONITORING, batch_size)

    def count_videos_by_status(self, status: VideoStatus) -> int:
        """
        获取指定状态视频的数量

        Args:
            status: 视频状态

        Returns:
            视频数量
        """
        with get_db_session() as session:
            result = session.execute(
                text("SELECT COUNT(*) FROM monitor_pool WHERE status = :status"),
                {"status": status.value}
            ).scalar()
            return result or 0

    def count_monitoring_videos(self) -> int:
        """获取监控中视频的数量"""
        return self.count_videos_by_status(VideoStatus.MONITORING)

    def update_video_views(
        self,
        bvid: str,
        view_today: int,
        like_count: Optional[int] = None,
        favorite_count: Optional[int] = None,
        reply_count: Optional[int] = None
    ) -> bool:
        """更新视频播放数据"""
        with get_db_session() as session:
            sql = """
                UPDATE monitor_pool
                SET view_today = :view_today,
                    last_collected = :last_collected,
                    updated_at = :updated_at
            """
            params = {
                "view_today": view_today,
                "last_collected": datetime.now(),
                "updated_at": datetime.now(),
                "bvid": bvid,
            }

            if like_count is not None:
                sql += ", like_count = :like_count"
                params["like_count"] = like_count
            if favorite_count is not None:
                sql += ", favorite_count = :favorite_count"
                params["favorite_count"] = favorite_count
            if reply_count is not None:
                sql += ", reply_count = :reply_count"
                params["reply_count"] = reply_count

            sql += " WHERE bvid = :bvid"

            result = session.execute(text(sql), params)
            return result.rowcount > 0

    def batch_update_view_today(self, video_views: List[dict]) -> int:
        """
        批量更新视频今日播放量

        Args:
            video_views: [{"bvid": str, "view_today": int, "like_count": int, ...}, ...]

        Returns:
            更新成功的数量
        """
        if not video_views:
            return 0

        now = datetime.now()
        updated = 0

        with get_db_session() as session:
            for item in video_views:
                try:
                    sql = """
                        UPDATE monitor_pool
                        SET view_today = :view_today,
                            last_collected = :last_collected,
                            updated_at = :updated_at
                    """
                    params = {
                        "view_today": item["view_today"],
                        "last_collected": now,
                        "updated_at": now,
                        "bvid": item["bvid"],
                    }

                    # 可选字段
                    if "like_count" in item and item["like_count"] is not None:
                        sql += ", like_count = :like_count"
                        params["like_count"] = item["like_count"]
                    if "favorite_count" in item and item["favorite_count"] is not None:
                        sql += ", favorite_count = :favorite_count"
                        params["favorite_count"] = item["favorite_count"]
                    if "reply_count" in item and item["reply_count"] is not None:
                        sql += ", reply_count = :reply_count"
                        params["reply_count"] = item["reply_count"]

                    sql += " WHERE bvid = :bvid"
                    result = session.execute(text(sql), params)
                    if result.rowcount > 0:
                        updated += 1
                except Exception as e:
                    print(f"Batch update view_today failed for {item.get('bvid')}: {e}")

        return updated

    def calculate_growth_rate(self, bvid: str) -> Optional[float]:
        """
        计算播放增速
        公式: (今日播放量 - 昨日播放量) / 昨日播放量 * 100%
        """
        video = self.get_video_by_bvid(bvid)
        if not video:
            return None

        if video.view_yesterday == 0:
            return 0.0

        growth_rate = round(
            (video.view_today - video.view_yesterday) / video.view_yesterday * 100,
            2
        )

        # 更新到数据库
        with get_db_session() as session:
            session.execute(
                text("""
                    UPDATE monitor_pool
                    SET growth_rate = :growth_rate, updated_at = :updated_at
                    WHERE bvid = :bvid
                """),
                {"growth_rate": growth_rate, "updated_at": datetime.now(), "bvid": bvid}
            )

        return growth_rate

    def roll_views(self, bvid: str) -> bool:
        """
        滚动播放数据
        将 view_today 赋值给 view_yesterday，然后清零 view_today
        """
        video = self.get_video_by_bvid(bvid)
        if not video:
            return False

        with get_db_session() as session:
            session.execute(
                text("""
                    UPDATE monitor_pool
                    SET view_yesterday = :view_yesterday,
                        view_today = 0,
                        updated_at = :updated_at
                    WHERE bvid = :bvid
                """),
                {"view_yesterday": video.view_today, "updated_at": datetime.now(), "bvid": bvid}
            )
        return True

    def update_video_status(self, bvid: str, status: VideoStatus) -> bool:
        """更新视频状态"""
        with get_db_session() as session:
            result = session.execute(
                text("""
                    UPDATE monitor_pool
                    SET status = :status, updated_at = :updated_at
                    WHERE bvid = :bvid
                """),
                {"status": status.value, "updated_at": datetime.now(), "bvid": bvid}
            )
            return result.rowcount > 0

    def update_video_channel(self, bvid: str, channel: str) -> bool:
        """更新视频赛道"""
        with get_db_session() as session:
            result = session.execute(
                text("""
                    UPDATE monitor_pool
                    SET channel = :channel, updated_at = :updated_at
                    WHERE bvid = :bvid
                """),
                {"channel": channel, "updated_at": datetime.now(), "bvid": bvid}
            )
            return result.rowcount > 0

    def update_video_growth_rate(self, bvid: str, growth_rate: float) -> bool:
        """更新视频增速"""
        with get_db_session() as session:
            result = session.execute(
                text("""
                    UPDATE monitor_pool
                    SET growth_rate = :growth_rate, updated_at = :updated_at
                    WHERE bvid = :bvid
                """),
                {"growth_rate": growth_rate, "updated_at": datetime.now(), "bvid": bvid}
            )
            return result.rowcount > 0

    def count_videos_by_status(self, status: VideoStatus) -> int:
        """统计指定状态的视频数量"""
        with get_db_session() as session:
            result = session.execute(
                text("SELECT COUNT(*) FROM monitor_pool WHERE status = :status"),
                {"status": status.value}
            ).scalar()
            return result or 0

    def delete_video(self, bvid: str) -> bool:
        """删除视频"""
        with get_db_session() as session:
            result = session.execute(
                text("DELETE FROM monitor_pool WHERE bvid = :bvid"),
                {"bvid": bvid}
            )
            return result.rowcount > 0

    def list_videos(
        self,
        channel: Optional[str] = None,
        status: Optional[VideoStatus] = None,
        order_by: str = "growth_rate",
        limit: int = 100,
        offset: int = 0
    ) -> List[Video]:
        """通用视频列表查询"""
        with get_db_session() as session:
            sql = """
                SELECT id, bvid, title, author, channel, keyword,
                       view_yesterday, view_today, growth_rate,
                       like_count, favorite_count, reply_count,
                       pubdate, cover_url, status,
                       first_seen, last_collected, created_at, updated_at
                FROM monitor_pool
                WHERE 1=1
            """
            params = {}

            if channel:
                sql += " AND channel = :channel"
                params["channel"] = channel
            if status:
                sql += " AND status = :status"
                params["status"] = status.value

            if order_by == "growth_rate":
                sql += " ORDER BY growth_rate DESC"
            elif order_by == "created_at":
                sql += " ORDER BY created_at DESC"
            elif order_by == "view_today":
                sql += " ORDER BY view_today DESC"

            sql += " LIMIT :limit OFFSET :offset"
            params["limit"] = limit
            params["offset"] = offset

            results = session.execute(text(sql), params).fetchall()
            return [self._row_to_video(row) for row in results]

    def _row_to_video(self, row) -> Video:
        """将数据库行转换为Video对象"""
        return Video(
            id=row[0],
            bvid=row[1],
            title=row[2] or "",
            author=row[3] or "",
            channel=row[4] or "",
            keyword=row[5] or "",
            view_yesterday=row[6] or 0,
            view_today=row[7] or 0,
            growth_rate=float(row[8] or 0),
            like_count=row[9] or 0,
            favorite_count=row[10] or 0,
            reply_count=row[11] or 0,
            pubdate=row[12],
            cover_url=row[13],
            status=VideoStatus(row[14]) if row[14] else VideoStatus.MONITORING,
            first_seen=row[15],
            last_collected=row[16],
            created_at=row[17],
            updated_at=row[18],
        )

    def _row_to_video_with_online(self, row) -> Video:
        """将数据库行（包含online_count）转换为Video对象"""
        return Video(
            id=row[0],
            bvid=row[1],
            title=row[2] or "",
            author=row[3] or "",
            channel=row[4] or "",
            keyword=row[5] or "",
            view_yesterday=row[6] or 0,
            view_today=row[7] or 0,
            growth_rate=float(row[8] or 0),
            like_count=row[9] or 0,
            favorite_count=row[10] or 0,
            reply_count=row[11] or 0,
            pubdate=row[12],
            cover_url=row[13],
            status=VideoStatus(row[14]) if row[14] else VideoStatus.MONITORING,
            first_seen=row[15],
            last_collected=row[16],
            created_at=row[17],
            updated_at=row[18],
            online_count=row[19] or 0,
        )
