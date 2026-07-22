"""
视频发现器
根据关键词发现新视频
"""
import asyncio
from typing import List, Optional, Callable, Generator, Any, Dict
from dataclasses import dataclass

from bilibili_api import video, Credential
from bilibili_api import search as bilibili_search
from bilibili_api.exceptions import ResponseException, NetworkException

from src.config import settings
from src.crawlers.anti_crawler import get_anti_crawler
from src.crawlers.daily_hot_api import normalize_channel
from src.models.video import Video, VideoStatus
from src.services.monitor_pool_service import MonitorPoolService
from src.utils.logger import safe_str


# 过滤条件
DEFAULT_MIN_VIEW_COUNT = 3000   # 最小播放量
DEFAULT_MIN_LIKE_COUNT = 100    # 最小点赞数


@dataclass
class VideoSearchResult:
    """视频搜索结果"""
    bvid: str
    title: str
    author: str
    view_count: int
    like_count: int
    pubdate: int  # Unix时间戳


@dataclass
class VideoDetail:
    """视频详情"""
    bvid: str
    title: str
    author: str
    channel: str
    view_count: int
    like_count: int
    favorite_count: int
    reply_count: int
    pubdate: int  # Unix时间戳
    cover_url: str
    cid: int = 0  # 视频分P cid，用于获取在线人数


class VideoDiscoverer:
    """视频发现器"""

    def __init__(
        self,
        credential: Optional[Credential] = None,
        monitor_service: Optional[MonitorPoolService] = None,
        min_view_count: int = DEFAULT_MIN_VIEW_COUNT,
        min_like_count: int = DEFAULT_MIN_LIKE_COUNT
    ):
        self.credential = self._create_credential(credential)
        self.monitor_service = monitor_service or MonitorPoolService()
        self.min_view_count = min_view_count
        self.min_like_count = min_like_count
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

    async def _search_videos_async(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20
    ) -> List[VideoSearchResult]:
        """异步搜索视频（延时由调用方控制）"""
        try:
            search_data = await bilibili_search.search(keyword=keyword, search_type=bilibili_search.SearchObjectType.VIDEO)
            results = []

            # bilibili-api返回的是dict，需要从result字段获取列表
            result_list = search_data.get("result", []) if isinstance(search_data, dict) else search_data

            for item in result_list:
                # 过滤直播等内容，只保留视频
                result_type = item.get("result_type", "")
                if result_type != "video":
                    continue

                # video类型的data是列表
                video_list = item.get("data", [])
                if not isinstance(video_list, list):
                    continue

                for video_data in video_list:
                    results.append(VideoSearchResult(
                        bvid=video_data.get("bvid", ""),
                        title=video_data.get("title", ""),
                        author=video_data.get("author", ""),
                        view_count=video_data.get("play", 0),
                        like_count=video_data.get("like", 0),
                        pubdate=video_data.get("pubdate", 0),
                    ))

                    if len(results) >= page_size:
                        break

                if len(results) >= page_size:
                    break

            return results

        except Exception as e:
            print(f"Search error: {e}")
            return []

    def search_videos(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20
    ) -> List[VideoSearchResult]:
        """搜索视频"""
        return self._sync(self._search_videos_async(keyword, page, page_size))

    async def _get_video_detail_async(self, bvid: str) -> Optional[VideoDetail]:
        """异步获取视频详情（延时由调用方控制）"""
        try:
            v = video.Video(bvid=bvid, credential=self.credential)
            video_data = await v.get_info()

            if not video_data.get("bvid"):
                return None

            stat = video_data.get("stat", {})

            # 获取视频分P的cid（取第一个分P）
            cid = 0
            pages = video_data.get("pages", [])
            if pages:
                cid = pages[0].get("cid", 0)

            return VideoDetail(
                bvid=bvid,
                title=video_data.get("title", ""),
                author=video_data.get("owner", {}).get("name", ""),
                channel=video_data.get("tname", ""),
                view_count=stat.get("view", 0),
                like_count=stat.get("like", 0),
                favorite_count=stat.get("favorite", 0),
                reply_count=stat.get("reply", 0),
                pubdate=video_data.get("pubdate", 0),
                cover_url=video_data.get("pic", ""),
                cid=cid,
            )

        except Exception as e:
            print(f"Get video detail error: {e}")
            return None

    def get_video_detail(self, bvid: str) -> Optional[VideoDetail]:
        """获取视频详情"""
        return self._sync(self._get_video_detail_async(bvid))

    def discover_by_keyword(
        self,
        keyword: str,
        max_pages: int = 5,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Video]:
        """
        根据关键词发现新视频

        Args:
            keyword: 搜索关键词
            max_pages: 最大搜索页数
            progress_callback: 进度回调函数 callback(current_page, total_pages)

        Returns:
            发现的新视频列表
        """
        discovered_videos = []

        for page in range(1, max_pages + 1):
            if progress_callback:
                progress_callback(page, max_pages)

            # 搜索视频
            search_results = self.search_videos(keyword, page=page)

            for result in search_results:
                # 过滤有效视频
                if not self._is_valid_video(result):
                    continue

                # 获取视频详情
                detail = self.get_video_detail(result.bvid)
                if not detail:
                    continue

                # 转换为Video对象
                video = self._detail_to_video(detail, keyword)

                # 检查是否已存在
                existing = self.monitor_service.get_video_by_bvid(video.bvid)
                if existing:
                    continue

                discovered_videos.append(video)

        return discovered_videos

    def discover_multi_keywords(
        self,
        keywords: List[str],
        max_pages_per_keyword: int = 3,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Generator[Video, None, None]:
        """
        根据多个关键词发现新视频（生成器模式，避免内存超限）

        Args:
            keywords: 关键词列表
            max_pages_per_keyword: 每个关键词最大搜索页数
            progress_callback: 进度回调函数 callback(keyword, current_page, total_pages)

        Yields:
            发现的新视频，边发现边返回
        """
        seen_bvids = set()

        for keyword in keywords:
            videos = self.discover_by_keyword(
                keyword,
                max_pages=max_pages_per_keyword,
                progress_callback=lambda page, total, kw=keyword: (
                    progress_callback and progress_callback(kw, page, total)
                )
            )

            for video in videos:
                if video.bvid not in seen_bvids:
                    seen_bvids.add(video.bvid)
                    yield video

    def _is_valid_video(self, result: VideoSearchResult) -> bool:
        """判断视频是否符合过滤条件"""
        return (
            (result.view_count or 0) >= self.min_view_count
            and (result.like_count or 0) >= self.min_like_count
        )

    def _detail_to_video(self, detail: VideoDetail, keyword: str) -> Video:
        """将VideoDetail转换为Video模型"""
        from datetime import datetime

        pubdate = None
        if detail.pubdate:
            pubdate = datetime.fromtimestamp(detail.pubdate)

        # 归一化赛道为21个标准中文赛道
        normalized_channel = normalize_channel(detail.channel)

        return Video(
            bvid=detail.bvid,
            title=detail.title,
            author=detail.author,
            channel=normalized_channel,
            keyword=keyword,
            view_yesterday=0,
            view_today=detail.view_count,
            growth_rate=0.0,
            like_count=detail.like_count,
            favorite_count=detail.favorite_count,
            reply_count=detail.reply_count,
            pubdate=pubdate,
            cover_url=detail.cover_url,
            status=VideoStatus.MONITORING,
        )

    def filter_valid_videos(self, videos: List[Video]) -> List[Video]:
        """过滤有效视频（播放量>3000, 点赞>100）"""
        return [
            video for video in videos
            if video.view_today >= self.min_view_count
            and video.like_count >= self.min_like_count
        ]

    def save_discovered_videos(
        self,
        videos: List[Video],
        skip_existing: bool = True
    ) -> tuple:
        """
        保存发现的新视频到监控池

        Returns:
            (success_count, skip_count, error_count)
        """
        success_count = 0
        skip_count = 0
        error_count = 0

        for video in videos:
            try:
                existing = self.monitor_service.get_video_by_bvid(video.bvid)
                if existing and skip_existing:
                    skip_count += 1
                    continue

                self.monitor_service.add_video(video)
                success_count += 1

            except ValueError:
                # 重复视频
                skip_count += 1
            except Exception as e:
                print(f"Error saving video {video.bvid}: {e}")
                error_count += 1

        return (success_count, skip_count, error_count)

    def save_discovered_videos_streaming(
        self,
        video_generator: Generator[Video, None, None],
        skip_existing: bool = True
    ) -> tuple:
        """
        流式保存发现的新视频到监控池（边发现边保存，避免内存超限）

        Args:
            video_generator: 视频生成器
            skip_existing: 是否跳过已存在的视频

        Returns:
            (success_count, skip_count, error_count, discovered_count)
        """
        success_count = 0
        skip_count = 0
        error_count = 0
        discovered_count = 0

        for video in video_generator:
            discovered_count += 1
            try:
                existing = self.monitor_service.get_video_by_bvid(video.bvid)
                if existing and skip_existing:
                    skip_count += 1
                    continue

                self.monitor_service.add_video(video)
                success_count += 1

            except ValueError:
                # 重复视频
                skip_count += 1
            except Exception as e:
                print(f"Error saving video {video.bvid}: {e}")
                error_count += 1

        return (success_count, skip_count, error_count, discovered_count)
