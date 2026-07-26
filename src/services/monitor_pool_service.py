"""
监控池服务层
"""
import json
from datetime import datetime
from typing import List, Optional, Generator, Dict

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.models.video import Video, VideoStatus
from src.models.author import AuthorInfo
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
                    (bvid, title, author, author_mid, channel, keyword, view_yesterday, view_today,
                     growth_rate, like_count, favorite_count, reply_count, pubdate,
                     cover_url, duration, tags, status, first_seen, last_collected, created_at, updated_at)
                    VALUES
                    (:bvid, :title, :author, :author_mid, :channel, :keyword, :view_yesterday, :view_today,
                     :growth_rate, :like_count, :favorite_count, :reply_count, :pubdate,
                     :cover_url, :duration, :tags, :status, :first_seen, :last_collected, :created_at, :updated_at)
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
                    "pubdate": video.pubdate,
                    "cover_url": video.cover_url,
                    "duration": video.duration or 0,
                    "tags": json.dumps(video.tags) if video.tags else None,
                    "status": video.status.value if isinstance(video.status, VideoStatus) else video.status,
                    "first_seen": video.first_seen or now,
                    "last_collected": video.last_collected,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            video.id = result.fetchone()[0]
            return video

    def add_video_channel(self, bvid: str, channel_name: str, is_primary: bool = True) -> bool:
        """
        添加视频与赛道的关联关系到video_channel表

        Args:
            bvid: 视频BVID
            channel_name: 赛道名称（标准赛道中文名）
            is_primary: 是否为主赛道

        Returns:
            是否添加成功
        """
        with get_db_session() as session:
            # 根据赛道名称查找赛道ID
            result = session.execute(
                text("SELECT channel_id FROM channel_config WHERE channel_name = :name"),
                {"name": channel_name}
            ).fetchone()

            if not result:
                # 如果找不到对应赛道，不写入关联关系
                return False

            channel_id = result[0]

            # 写入video_channel表
            try:
                session.execute(
                    text("""
                        INSERT INTO video_channel (video_bvid, channel_id, is_primary, status, created_at)
                        VALUES (:bvid, :channel_id, :is_primary, :status, :created_at)
                        ON CONFLICT (video_bvid, channel_id) DO NOTHING
                    """),
                    {
                        "bvid": bvid,
                        "channel_id": channel_id,
                        "is_primary": is_primary,
                        "status": "monitoring",
                        "created_at": datetime.now(),
                    }
                )
                return True
            except Exception as e:
                print(f"Failed to add video_channel: {e}")
                return False

    def add_video_channel_with_status(
        self,
        bvid: str,
        channel_name: str,
        status: str,
        is_primary: bool = True
    ) -> bool:
        """
        添加视频与赛道的关联关系到video_channel表（带状态）

        Args:
            bvid: 视频BVID
            channel_name: 赛道名称（标准赛道中文名）
            status: 状态 ('monitoring' / 'featured' / 'declined')
            is_primary: 是否为主赛道

        Returns:
            是否添加成功
        """
        with get_db_session() as session:
            # 根据赛道名称查找赛道ID
            result = session.execute(
                text("SELECT channel_id FROM channel_config WHERE channel_name = :name"),
                {"name": channel_name}
            ).fetchone()

            if not result:
                # 如果找不到对应赛道，不写入关联关系
                return False

            channel_id = result[0]

            # 写入video_channel表
            try:
                session.execute(
                    text("""
                        INSERT INTO video_channel (video_bvid, channel_id, is_primary, status, created_at)
                        VALUES (:bvid, :channel_id, :is_primary, :status, :created_at)
                        ON CONFLICT (video_bvid, channel_id) DO UPDATE SET status = :status
                    """),
                    {
                        "bvid": bvid,
                        "channel_id": channel_id,
                        "is_primary": is_primary,
                        "status": status,
                        "created_at": datetime.now(),
                    }
                )
                return True
            except Exception as e:
                print(f"Failed to add video_channel: {e}")
                return False

    def get_video_by_bvid(self, bvid: str) -> Optional[Video]:
        """根据bvid获取视频"""
        with get_db_session() as session:
            result = session.execute(
                text("""
                    SELECT mp.id, mp.bvid, mp.title, mp.author, mp.author_mid, mp.channel as mp_channel,
                           cc.channel_name,
                           mp.keyword,
                           mp.view_yesterday, mp.view_today, mp.growth_rate,
                           mp.like_count, mp.favorite_count, mp.reply_count,
                           mp.coin_count, mp.share_count, mp.danmu_count,
                           mp.online_count, mp.max_online_today,
                           mp.pubdate, mp.cover_url, mp.duration, mp.tags,
                           mp.first_seen, mp.last_collected, mp.created_at, mp.updated_at,
                           vc.status as video_channel_status
                    FROM monitor_pool mp
                    LEFT JOIN video_channel vc ON mp.bvid = vc.video_bvid AND vc.is_primary = TRUE
                    LEFT JOIN channel_config cc ON vc.channel_id = cc.channel_id
                       AND cc.status = 'active' AND cc.created_by = 1
                    WHERE mp.bvid = :bvid
                """),
                {"bvid": bvid}
            ).fetchone()

            if result is None:
                return None

            # 状态从 video_channel 获取，默认为 monitoring
            video_channel_status = result[27] if result[27] else "monitoring"
            status = VideoStatus(video_channel_status) if video_channel_status in ["featured", "monitoring", "declined"] else VideoStatus.MONITORING

            return Video(
                id=result[0],
                bvid=result[1],
                title=result[2] or "",
                author=result[3] or "",
                author_mid=result[4],
                # 优先使用 channel_config 的 channel_name，否则使用 monitor_pool.channel
                channel=result[6] if result[6] else (result[5] or ""),
                keyword=result[7] or "",
                view_yesterday=result[8] or 0,
                view_today=result[9] or 0,
                growth_rate=float(result[10] or 0),
                like_count=result[11] or 0,
                favorite_count=result[12] or 0,
                reply_count=result[13] or 0,
                coin_count=result[14] or 0,
                share_count=result[15] or 0,
                danmu_count=result[16] or 0,
                online_count=result[17] or 0,
                max_online_today=result[18] or 0,
                pubdate=result[19],
                cover_url=result[20],
                duration=result[21] or 0,
                tags=result[22],
                status=status,
                first_seen=result[23],
                last_collected=result[24],
                created_at=result[25],
                updated_at=result[26],
            )

    def get_videos_by_channel(self, channel: str, limit: int = 100) -> List[Video]:
        """根据赛道获取视频列表"""
        with get_db_session() as session:
            # 从 video_channel + channel_config 读取赛道信息
            # 状态从 video_channel 读取，其他数据从 monitor_pool 读取
            results = session.execute(
                text("""
                    SELECT mp.id, mp.bvid, mp.title, mp.author, mp.channel as mp_channel,
                           cc.channel_name,
                           mp.keyword,
                           mp.view_yesterday, mp.view_today, mp.growth_rate,
                           mp.like_count, mp.favorite_count, mp.reply_count,
                           mp.coin_count, mp.share_count, mp.danmu_count,
                           mp.online_count, mp.max_online_today,
                           mp.pubdate, mp.cover_url,
                           mp.first_seen, mp.last_collected, mp.created_at, mp.updated_at,
                           vc.status as channel_status
                    FROM monitor_pool mp
                    LEFT JOIN video_channel vc ON mp.bvid = vc.video_bvid AND vc.is_primary = TRUE
                    LEFT JOIN channel_config cc ON vc.channel_id = cc.channel_id
                       AND cc.status = 'active' AND cc.created_by = 1
                    WHERE cc.channel_name = :channel
                    ORDER BY mp.growth_rate DESC
                    LIMIT :limit
                """),
                {"channel": channel, "limit": limit}
            ).fetchall()

            return [self._row_to_video_with_channel_from_vc(row) for row in results]

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
            # 从 video_channel + channel_config 读取赛道和状态信息
            results = session.execute(
                text("""
                    SELECT mp.id, mp.bvid, mp.title, mp.author, mp.channel as mp_channel,
                           cc.channel_name,
                           mp.keyword,
                           mp.view_yesterday, mp.view_today, mp.growth_rate,
                           mp.like_count, mp.favorite_count, mp.reply_count,
                           mp.coin_count, mp.share_count, mp.danmu_count,
                           mp.online_count, mp.max_online_today,
                           mp.pubdate, mp.cover_url,
                           mp.first_seen, mp.last_collected, mp.created_at, mp.updated_at,
                           vc.status as channel_status
                    FROM monitor_pool mp
                    LEFT JOIN video_channel vc ON mp.bvid = vc.video_bvid AND vc.is_primary = TRUE
                    LEFT JOIN channel_config cc ON vc.channel_id = cc.channel_id
                       AND cc.status = 'active' AND cc.created_by = 1
                    WHERE vc.status = :status AND cc.channel_name = :channel
                    ORDER BY mp.view_today DESC
                    LIMIT :limit
                """),
                {"status": status.value, "channel": channel, "limit": limit}
            ).fetchall()

            return [self._row_to_video_with_channel_from_vc(row) for row in results]

    def get_featured_videos_by_channel(
        self,
        channel: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Video]:
        """获取指定赛道的已上榜视频（按在线人数降序）"""
        with get_db_session() as session:
            # 使用子查询先去除重复视频，再按在线人数排序
            # 原始查询可能因为 JOIN 同一视频在多个赛道而产生重复
            results = session.execute(
                text("""
                    SELECT * FROM (
                        SELECT DISTINCT ON (mp.bvid) mp.id, mp.bvid, mp.title, mp.author, mp.channel, mp.keyword,
                               mp.view_yesterday, mp.view_today, mp.growth_rate,
                               mp.like_count, mp.favorite_count, mp.reply_count,
                               mp.coin_count, mp.share_count, mp.danmu_count,
                               mp.online_count, mp.max_online_today,
                               mp.pubdate, mp.cover_url, mp.duration, mp.tags,
                               mp.first_seen, mp.last_collected, mp.created_at, mp.updated_at,
                               vc.status as channel_status
                        FROM monitor_pool mp
                        JOIN video_channel vc ON mp.bvid = vc.video_bvid
                        JOIN channel_config cc ON vc.channel_id = cc.channel_id
                           AND cc.status = 'active' AND cc.created_by = 1
                        WHERE vc.status = 'featured' AND (:channel = '' OR cc.channel_name = :channel)
                        ORDER BY mp.bvid, mp.online_count DESC
                    ) AS unique_videos
                    ORDER BY online_count DESC, id DESC
                    LIMIT :limit OFFSET :offset
                """),
                {"channel": channel, "limit": limit, "offset": offset}
            ).fetchall()

            return [self._row_to_video_with_channel_from_vc(row) for row in results]

    def get_featured_videos_from_channel(
        self,
        limit: int = 1000,
    ) -> List[Video]:
        """
        从video_channel表获取所有featured状态的视频

        Args:
            limit: 最大返回数量

        Returns:
            Video列表
        """
        with get_db_session() as session:
            results = session.execute(
                text("""
                    SELECT mp.id, mp.bvid, mp.title, mp.author, mp.channel, mp.keyword,
                           mp.view_yesterday, mp.view_today, mp.growth_rate,
                           mp.like_count, mp.favorite_count, mp.reply_count,
                           mp.coin_count, mp.share_count, mp.danmu_count,
                           mp.online_count, mp.max_online_today,
                           mp.pubdate, mp.cover_url,
                           mp.first_seen, mp.last_collected, mp.created_at, mp.updated_at,
                           vc.status as channel_status
                    FROM monitor_pool mp
                    JOIN video_channel vc ON mp.bvid = vc.video_bvid
                    WHERE vc.status = 'featured'
                    ORDER BY mp.online_count DESC
                    LIMIT :limit
                """),
                {"limit": limit}
            ).fetchall()

            return [self._row_to_video_with_online_from_channel(row) for row in results]

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
        reply_count: Optional[int] = None,
        coin_count: Optional[int] = None,
        share_count: Optional[int] = None,
        danmu_count: Optional[int] = None,
        online_count: Optional[int] = None
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
            if coin_count is not None:
                sql += ", coin_count = :coin_count"
                params["coin_count"] = coin_count
            if share_count is not None:
                sql += ", share_count = :share_count"
                params["share_count"] = share_count
            if danmu_count is not None:
                sql += ", danmu_count = :danmu_count"
                params["danmu_count"] = danmu_count
            if online_count is not None:
                sql += ", online_count = :online_count"
                params["online_count"] = online_count

            sql += " WHERE bvid = :bvid"

            result = session.execute(text(sql), params)
            return result.rowcount > 0

    def update_author_mid_if_null(self, bvid: str, author_mid: str) -> bool:
        """
        仅当视频的author_mid为空时更新

        Args:
            bvid: 视频BVID
            author_mid: 作者MID

        Returns:
            是否更新成功
        """
        if not author_mid:
            return False

        with get_db_session() as session:
            try:
                session.execute(
                    text("""
                        UPDATE monitor_pool
                        SET author_mid = :author_mid, updated_at = :updated_at
                        WHERE bvid = :bvid AND author_mid IS NULL
                    """),
                    {
                        "bvid": bvid,
                        "author_mid": author_mid,
                        "updated_at": datetime.now(),
                    }
                )
                return True
            except Exception as e:
                print(f"Update author_mid error: {e}")
                return False

    def get_author_info(self, mid: str) -> Optional[AuthorInfo]:
        """
        根据MID获取作者信息

        Args:
            mid: 作者MID

        Returns:
            AuthorInfo对象，如果不存在返回None
        """
        with get_db_session() as session:
            result = session.execute(
                text("""
                    SELECT id, mid, name, avatar, fans, following, archive_count,
                           total_view, total_liked, first_collected, last_updated, created_at
                    FROM author_info
                    WHERE mid = :mid
                """),
                {"mid": mid}
            ).fetchone()

            if result is None:
                return None

            return AuthorInfo(
                id=result[0],
                mid=result[1],
                name=result[2] or "",
                avatar=result[3],
                fans=result[4] or 0,
                following=result[5] or 0,
                archive_count=result[6] or 0,
                total_view=result[7] or 0,
                total_liked=result[8] or 0,
                first_collected=result[9],
                last_updated=result[10],
                created_at=result[11],
            )

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

    def update_max_online_today(self, bvid: str, max_online: int) -> bool:
        """
        更新视频当日最大在线人数
        如果新值大于当前值，则更新

        Args:
            bvid: 视频BVID
            max_online: 新的在线人数

        Returns:
            是否更新成功
        """
        with get_db_session() as session:
            result = session.execute(
                text("""
                    UPDATE monitor_pool
                    SET max_online_today = GREATEST(max_online_today, :max_online),
                        updated_at = :updated_at
                    WHERE bvid = :bvid
                """),
                {"max_online": max_online, "updated_at": datetime.now(), "bvid": bvid}
            )
            return result.rowcount > 0

    def update_video_channel_status(self, bvid: str, channel_id: str, status: VideoStatus) -> bool:
        """
        更新视频在指定赛道中的状态

        Args:
            bvid: 视频BVID
            channel_id: 赛道ID
            status: 新的状态

        Returns:
            是否更新成功
        """
        with get_db_session() as session:
            result = session.execute(
                text("""
                    UPDATE video_channel
                    SET status = :status
                    WHERE video_bvid = :bvid AND channel_id = :channel_id
                """),
                {"bvid": bvid, "channel_id": channel_id, "status": status.value}
            )
            return result.rowcount > 0

    def get_video_status_by_channel(self, bvid: str, channel_id: str) -> Optional[VideoStatus]:
        """
        获取视频在指定赛道中的状态

        Args:
            bvid: 视频BVID
            channel_id: 赛道ID

        Returns:
            视频状态，如果不存在返回None
        """
        with get_db_session() as session:
            result = session.execute(
                text("""
                    SELECT status FROM video_channel
                    WHERE video_bvid = :bvid AND channel_id = :channel_id
                """),
                {"bvid": bvid, "channel_id": channel_id}
            ).fetchone()

            if result and result[0]:
                return VideoStatus(result[0])
            return None

    def get_video_channels(self, bvid: str) -> List[Dict]:
        """
        获取视频关联的所有赛道

        Args:
            bvid: 视频BVID

        Returns:
            赛道列表 [{"channel_id": str, "status": VideoStatus, "is_primary": bool}, ...]
        """
        with get_db_session() as session:
            results = session.execute(
                text("""
                    SELECT vc.channel_id, vc.status, vc.is_primary, cc.channel_name
                    FROM video_channel vc
                    JOIN channel_config cc ON vc.channel_id = cc.channel_id
                    WHERE vc.video_bvid = :bvid
                """),
                {"bvid": bvid}
            ).fetchall()

            return [
                {
                    "channel_id": row[0],
                    "status": VideoStatus(row[1]) if row[1] else VideoStatus.MONITORING,
                    "is_primary": row[2],
                    "channel_name": row[3],
                }
                for row in results
            ]

    def update_video_max_online_today(self, bvid: str, max_online_today: int) -> bool:
        """
        重置视频当日最大在线人数

        Args:
            bvid: 视频BVID
            max_online_today: 当日最大在线人数（通常为0）

        Returns:
            是否更新成功
        """
        with get_db_session() as session:
            result = session.execute(
                text("""
                    UPDATE monitor_pool
                    SET max_online_today = :max_online_today, updated_at = :updated_at
                    WHERE bvid = :bvid
                """),
                {"bvid": bvid, "max_online_today": max_online_today, "updated_at": datetime.now()}
            )
            return result.rowcount > 0

    def update_video_first_featured_at(self, bvid: str, featured_at: datetime) -> bool:
        """
        更新视频首次上榜时间

        Args:
            bvid: 视频BVID
            featured_at: 首次上榜时间

        Returns:
            是否更新成功
        """
        with get_db_session() as session:
            result = session.execute(
                text("""
                    UPDATE monitor_pool
                    SET first_featured_at = :featured_at, updated_at = :updated_at
                    WHERE bvid = :bvid
                """),
                {"bvid": bvid, "featured_at": featured_at, "updated_at": datetime.now()}
            )
            return result.rowcount > 0

    def update_max_online_ever(self, bvid: str, max_online: int) -> bool:
        """
        更新视频历史最大在线峰值（只增不减）

        Args:
            bvid: 视频BVID
            max_online: 最大在线人数

        Returns:
            是否更新成功
        """
        with get_db_session() as session:
            result = session.execute(
                text("""
                    UPDATE monitor_pool
                    SET max_online_ever = GREATEST(max_online_ever, :max_online),
                        updated_at = :updated_at
                    WHERE bvid = :bvid
                """),
                {"bvid": bvid, "max_online": max_online, "updated_at": datetime.now()}
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
            # 从 video_channel + channel_config 读取赛道信息
            # 过滤条件：channel_config.status = 'active' AND channel_config.created_by = 1
            sql = """
                SELECT mp.id, mp.bvid, mp.title, mp.author, mp.channel as mp_channel,
                       cc.channel_name,
                       mp.keyword,
                       mp.view_yesterday, mp.view_today, mp.growth_rate,
                       mp.like_count, mp.favorite_count, mp.reply_count,
                       mp.pubdate, mp.cover_url, mp.status,
                       mp.first_seen, mp.last_collected, mp.created_at, mp.updated_at
                FROM monitor_pool mp
                LEFT JOIN video_channel vc ON mp.bvid = vc.video_bvid AND vc.is_primary = TRUE
                LEFT JOIN channel_config cc ON vc.channel_id = cc.channel_id
                   AND cc.status = 'active' AND cc.created_by = 1
                WHERE 1=1
            """
            params = {}

            if channel:
                # 使用 channel_config 的 channel_name 进行过滤
                sql += " AND cc.channel_name = :channel"
                params["channel"] = channel
            if status:
                sql += " AND mp.status = :status"
                params["status"] = status.value

            if order_by == "growth_rate":
                sql += " ORDER BY mp.growth_rate DESC"
            elif order_by == "created_at":
                sql += " ORDER BY mp.created_at DESC"
            elif order_by == "view_today":
                sql += " ORDER BY mp.view_today DESC"

            sql += " LIMIT :limit OFFSET :offset"
            params["limit"] = limit
            params["offset"] = offset

            results = session.execute(text(sql), params).fetchall()
            return [self._row_to_video_with_channel(row) for row in results]

    def _row_to_video_with_channel(self, row) -> Video:
        """将数据库行转换为Video对象，channel从channel_config读取"""
        return Video(
            id=row[0],
            bvid=row[1],
            title=row[2] or "",
            author=row[3] or "",
            # 优先使用 channel_config 的 channel_name，否则使用 monitor_pool.channel
            channel=row[5] if row[5] else (row[4] or ""),
            keyword=row[6] or "",
            view_yesterday=row[7] or 0,
            view_today=row[8] or 0,
            growth_rate=float(row[9] or 0),
            like_count=row[10] or 0,
            favorite_count=row[11] or 0,
            reply_count=row[12] or 0,
            pubdate=row[13],
            cover_url=row[14],
            status=VideoStatus(row[15]) if row[15] else VideoStatus.MONITORING,
            first_seen=row[16],
            last_collected=row[17],
            created_at=row[18],
            updated_at=row[19],
        )

    def _row_to_video_with_channel_from_vc(self, row) -> Video:
        """将数据库行（从video_channel联表查询）转换为Video对象，channel从channel_config读取"""
        # SQL列顺序: mp.id(0), bvid(1), title(2), author(3), channel(4), keyword(5),
        # view_yesterday(6), view_today(7), growth_rate(8), like_count(9), favorite_count(10),
        # reply_count(11), coin_count(12), share_count(13), danmu_count(14), online_count(15),
        # max_online_today(16), pubdate(17), cover_url(18), duration(19), tags(20),
        # first_seen(21), last_collected(22), created_at(23), updated_at(24), status(25)
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
            coin_count=row[12] or 0,
            share_count=row[13] or 0,
            danmu_count=row[14] or 0,
            online_count=row[15] or 0,
            max_online_today=row[16] or 0,
            pubdate=row[17],
            cover_url=row[18],
            duration=row[19] or 0,
            tags=row[20],
            status=VideoStatus(row[25]) if row[25] else VideoStatus.MONITORING,
            first_seen=row[21],
            last_collected=row[22],
            created_at=row[23],
            updated_at=row[24],
        )

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

    def _row_to_video_with_online_from_channel(self, row) -> Video:
        """将数据库行（从video_channel联表查询，包含channel_status）转换为Video对象"""
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
            coin_count=row[12] or 0,
            share_count=row[13] or 0,
            danmu_count=row[14] or 0,
            online_count=row[15] or 0,
            max_online_today=row[16] or 0,
            pubdate=row[17],
            cover_url=row[18],
            status=VideoStatus(row[23]) if row[23] else VideoStatus.MONITORING,
            first_seen=row[19],
            last_collected=row[20],
            created_at=row[21],
            updated_at=row[22],
        )

    def set_need_author_collect(self, bvid: str) -> bool:
        """
        设置视频需要采集UP主信息标记

        Args:
            bvid: 视频BVID

        Returns:
            是否设置成功
        """
        with get_db_session() as session:
            try:
                session.execute(
                    text("""
                        UPDATE monitor_pool
                        SET need_author_collect = TRUE, updated_at = :updated_at
                        WHERE bvid = :bvid
                    """),
                    {
                        "bvid": bvid,
                        "updated_at": datetime.now(),
                    }
                )
                return True
            except Exception as e:
                print(f"Set need_author_collect error: {e}")
                return False

    def iter_videos_need_author_collect(self, batch_size: int = 100) -> Generator[Video, None, None]:
        """
        分批迭代获取需要采集UP主信息的视频（生成器模式）

        Args:
            batch_size: 每批获取数量

        Yields:
            Video 对象
        """
        offset = 0
        while True:
            with get_db_session() as session:
                results = session.execute(
                    text("""
                        SELECT id, bvid, title, author, author_mid, channel, keyword,
                               view_yesterday, view_today, growth_rate,
                               like_count, favorite_count, reply_count,
                               pubdate, cover_url, status,
                               first_seen, last_collected, created_at, updated_at
                        FROM monitor_pool
                        WHERE need_author_collect = TRUE
                          AND author_mid IS NOT NULL
                          AND author_mid != ''
                        ORDER BY id
                        LIMIT :limit OFFSET :offset
                    """),
                    {"limit": batch_size, "offset": offset}
                ).fetchall()

                if not results:
                    break

                for row in results:
                    yield self._row_to_video(row)

                if len(results) < batch_size:
                    break

                offset += batch_size

    def reset_need_author_collect(self, bvid: str) -> bool:
        """
        重置视频的UP主信息采集标记

        Args:
            bvid: 视频BVID

        Returns:
            是否重置成功
        """
        with get_db_session() as session:
            try:
                session.execute(
                    text("""
                        UPDATE monitor_pool
                        SET need_author_collect = FALSE, updated_at = :updated_at
                        WHERE bvid = :bvid
                    """),
                    {
                        "bvid": bvid,
                        "updated_at": datetime.now(),
                    }
                )
                return True
            except Exception as e:
                print(f"Reset need_author_collect error: {e}")
                return False

    def reset_need_author_collect_batch(self, bvids: List[str]) -> int:
        """
        批量重置视频的UP主信息采集标记

        Args:
            bvids: 视频BVID列表

        Returns:
            重置成功的数量
        """
        if not bvids:
            return 0

        with get_db_session() as session:
            try:
                result = session.execute(
                    text("""
                        UPDATE monitor_pool
                        SET need_author_collect = FALSE, updated_at = :updated_at
                        WHERE bvid = ANY(:bvids)
                    """),
                    {
                        "bvids": bvids,
                        "updated_at": datetime.now(),
                    }
                )
                return result.rowcount
            except Exception as e:
                print(f"Batch reset need_author_collect error: {e}")
                return 0

    def acquire_author_collect_lock(self, lock_holder: str, expire_seconds: int = 3600) -> bool:
        """
        获取UP主信息采集分布式锁
        使用数据库实现，确保只有一个进程执行采集

        Args:
            lock_holder: 锁持有者标识
            expire_seconds: 锁过期时间（秒）

        Returns:
            是否成功获取锁
        """
        now = datetime.now()
        expires_at = datetime.now()

        with get_db_session() as session:
            try:
                # 先尝试清理过期锁
                session.execute(
                    text("""
                        UPDATE author_collect_lock
                        SET locked_by = NULL, locked_at = NULL, expires_at = NULL
                        WHERE lock_name = 'author_collect'
                          AND expires_at IS NOT NULL
                          AND expires_at < :now
                    """),
                    {"now": now}
                )

                # 尝试获取锁
                result = session.execute(
                    text("""
                        UPDATE author_collect_lock
                        SET locked_by = :lock_holder,
                            locked_at = :locked_at,
                            expires_at = :expires_at
                        WHERE lock_name = 'author_collect'
                          AND (locked_by IS NULL OR expires_at < :now)
                    """),
                    {
                        "lock_holder": lock_holder,
                        "locked_at": now,
                        "expires_at": expires_at,
                        "now": now,
                    }
                )

                return result.rowcount > 0
            except Exception as e:
                print(f"Acquire author_collect_lock error: {e}")
                return False

    def release_author_collect_lock(self, lock_holder: str) -> bool:
        """
        释放UP主信息采集分布式锁

        Args:
            lock_holder: 锁持有者标识

        Returns:
            是否成功释放锁
        """
        with get_db_session() as session:
            try:
                result = session.execute(
                    text("""
                        UPDATE author_collect_lock
                        SET locked_by = NULL, locked_at = NULL, expires_at = NULL
                        WHERE lock_name = 'author_collect'
                          AND locked_by = :lock_holder
                    """),
                    {"lock_holder": lock_holder}
                )
                return result.rowcount > 0
            except Exception as e:
                print(f"Release author_collect_lock error: {e}")
                return False
