"""
UP主信息采集器
使用bilibili-api-python采集UP主信息
"""
import asyncio
import random
from datetime import datetime
from typing import Optional, Dict, Any

from bilibili_api import user, Credential
from bilibili_api.exceptions import ResponseException, NetworkException

from src.config import settings
from src.models.author import AuthorInfo
from src.crawlers.anti_crawler import get_anti_crawler
from src.utils.database import get_db_session
from sqlalchemy import text


class AuthorInfoCollector:
    """UP主信息采集器"""

    def __init__(self, credential: Optional[Credential] = None):
        self.credential = self._create_credential(credential)
        self.anti_crawler = get_anti_crawler()

    def _parse_cookie(self, cookie_str: str) -> Dict[str, str]:
        """解析Cookie字符串为字典"""
        result = {}
        if not cookie_str:
            return result
        for item in cookie_str.split(";"):
            item = item.strip()
            if "=" in item:
                key, value = item.split("=", 1)
                result[key.strip()] = value.strip()
        return result

    def _create_credential(self, credential: Optional[Credential] = None) -> Credential:
        """创建认证凭证"""
        if credential:
            return credential
        if settings.BILI_COOKIE:
            cookie_dict = self._parse_cookie(settings.BILI_COOKIE)
            return Credential(
                sessdata=cookie_dict.get("SESSDATA"),
                bili_jct=cookie_dict.get("bili_jct"),
                buvid3=cookie_dict.get("BUVID3")
            )
        return Credential()

    def _sync(self, coro):
        """将协程转换为同步调用"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

    async def _get_user_info_async(self, mid: str) -> Optional[Dict[str, Any]]:
        """异步获取用户基本信息"""
        try:
            u = user.User(uid=int(mid), credential=self.credential)
            user_info = await u.get_user_info()

            return {
                "mid": str(mid),
                "name": user_info.get("name", ""),
                "avatar": user_info.get("face", ""),
            }
        except Exception as e:
            print(f"Get user info error for mid {mid}: {e}")
            return None

    async def _get_relation_stats_async(self, mid: str) -> Optional[Dict[str, Any]]:
        """异步获取用户关系数据（粉丝、关注数）"""
        try:
            u = user.User(uid=int(mid), credential=self.credential)
            relation_stats = await u.get_relation_info()

            return {
                "fans": relation_stats.get("follower", 0),
                "following": relation_stats.get("following", 0),
            }
        except Exception as e:
            print(f"Get relation stats error for mid {mid}: {e}")
            return None

    async def _get_up_stats_async(self, mid: str) -> Optional[Dict[str, Any]]:
        """异步获取UP主作品统计"""
        try:
            u = user.User(uid=int(mid), credential=self.credential)
            up_stats = await u.get_overview_stat()

            return {
                "archive_count": up_stats.get("video", 0),
                "total_view": 0,  # overview_stat 不包含总播放
                "total_liked": 0,  # overview_stat 不包含总获赞
            }
        except Exception as e:
            print(f"Get up stats error for mid {mid}: {e}")
            return None

    async def _collect_author_info_async(self, mid: str) -> Optional[AuthorInfo]:
        """异步采集UP主完整信息"""
        # 应用延时
        self.anti_crawler.apply_delay()

        # 获取基本信息
        user_info = await self._get_user_info_async(mid)
        if not user_info:
            return None

        author = AuthorInfo(
            mid=user_info["mid"],
            name=user_info["name"],
            avatar=user_info["avatar"],
        )

        # 固定间隔 + 随机偏移，降低触发反爬概率
        await asyncio.sleep(random.uniform(2.5, 4.5))

        # 获取关系数据
        relation_stats = await self._get_relation_stats_async(mid)
        if relation_stats:
            author.fans = relation_stats.get("fans", 0)
            author.following = relation_stats.get("following", 0)

        # 固定间隔 + 随机偏移，降低触发反爬概率
        await asyncio.sleep(random.uniform(2.5, 4.5))

        # 获取作品统计
        up_stats = await self._get_up_stats_async(mid)
        if up_stats:
            author.archive_count = up_stats.get("archive_count", 0)
            author.total_view = up_stats.get("total_view", 0)
            author.total_liked = up_stats.get("total_liked", 0)

        author.last_updated = datetime.now()

        return author

    def collect_author_info(self, mid: str) -> Optional[AuthorInfo]:
        """采集UP主信息（同步方法）"""
        return self._sync(self._collect_author_info_async(mid))

    def get_author_info_from_video(self, video_data: Dict[str, Any]) -> Optional[str]:
        """
        从视频数据中提取UP主MID

        Args:
            video_data: 视频详情数据

        Returns:
            UP主MID字符串，如果不存在返回None
        """
        # 优先从owner获取mid
        owner = video_data.get("owner", {})
        mid = owner.get("mid")
        if mid:
            return str(mid)

        # 如果没有mid，尝试从视频URL或其他字段提取
        # B站视频页面URL格式: https://www.bilibili.com/video/BVxxxxxx
        return None

    def save_author_info(self, author: AuthorInfo) -> bool:
        """
        保存UP主信息到数据库

        Args:
            author: AuthorInfo对象

        Returns:
            是否保存成功
        """
        with get_db_session() as session:
            try:
                # 检查是否已存在
                result = session.execute(
                    text("SELECT id FROM author_info WHERE mid = :mid"),
                    {"mid": author.mid}
                ).fetchone()

                now = datetime.now()

                if result:
                    # 更新现有记录
                    session.execute(
                        text("""
                            UPDATE author_info
                            SET name = :name, avatar = :avatar, fans = :fans,
                                following = :following, archive_count = :archive_count,
                                total_view = :total_view, total_liked = :total_liked,
                                last_updated = :last_updated
                            WHERE mid = :mid
                        """),
                        {
                            "mid": author.mid,
                            "name": author.name,
                            "avatar": author.avatar,
                            "fans": author.fans,
                            "following": author.following,
                            "archive_count": author.archive_count,
                            "total_view": author.total_view,
                            "total_liked": author.total_liked,
                            "last_updated": now,
                        }
                    )
                else:
                    # 插入新记录
                    session.execute(
                        text("""
                            INSERT INTO author_info
                            (mid, name, avatar, fans, following, archive_count,
                             total_view, total_liked, first_collected, last_updated, created_at)
                            VALUES
                            (:mid, :name, :avatar, :fans, :following, :archive_count,
                             :total_view, :total_liked, :first_collected, :last_updated, :created_at)
                        """),
                        {
                            "mid": author.mid,
                            "name": author.name,
                            "avatar": author.avatar,
                            "fans": author.fans,
                            "following": author.following,
                            "archive_count": author.archive_count,
                            "total_view": author.total_view,
                            "total_liked": author.total_liked,
                            "first_collected": now,
                            "last_updated": now,
                            "created_at": now,
                        }
                    )

                return True

            except Exception as e:
                print(f"Save author info error: {e}")
                return False

    def update_monitor_pool_author_mid(self, bvid: str, mid: str) -> bool:
        """
        更新监控池中视频的author_mid字段

        Args:
            bvid: 视频BVID
            mid: UP主MID

        Returns:
            是否更新成功
        """
        with get_db_session() as session:
            try:
                session.execute(
                    text("""
                        UPDATE monitor_pool
                        SET author_mid = :mid, updated_at = :updated_at
                        WHERE bvid = :bvid AND (author_mid IS NULL OR author_mid != :mid)
                    """),
                    {
                        "bvid": bvid,
                        "mid": mid,
                        "updated_at": datetime.now(),
                    }
                )
                return True
            except Exception as e:
                print(f"Update monitor pool author_mid error: {e}")
                return False

    def collect_and_save(self, mid: str) -> Optional[AuthorInfo]:
        """
        采集并保存UP主信息

        Args:
            mid: UP主MID

        Returns:
            保存的AuthorInfo对象，失败返回None
        """
        author = self.collect_author_info(mid)
        if not author:
            return None

        if self.save_author_info(author):
            return author
        return None

    def collect_author_by_bvid(self, bvid: str, video_data: Dict[str, Any]) -> Optional[AuthorInfo]:
        """
        根据视频BVID采集UP主信息

        Args:
            bvid: 视频BVID
            video_data: 视频详情数据（包含owner.mid）

        Returns:
            保存的AuthorInfo对象，失败返回None
        """
        mid = self.get_author_info_from_video(video_data)
        if not mid:
            print(f"Cannot extract mid from video {bvid}")
            return None

        # 更新视频的author_mid
        self.update_monitor_pool_author_mid(bvid, mid)

        # 采集并保存UP主信息
        return self.collect_and_save(mid)
