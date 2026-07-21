"""
视频数据更新器
每日批量更新监控视频的播放数据
"""
import asyncio
from datetime import datetime
from typing import List, Optional, Callable, Dict, Any
from dataclasses import dataclass

from bilibili_api import video, Credential
from bilibili_api.exceptions import ResponseException, NetworkException

from src.config import settings
from src.crawlers.anti_crawler import get_anti_crawler
from src.services.monitor_pool_service import MonitorPoolService
from src.services.hot_judge import HotJudgeService


@dataclass
class VideoUpdateResult:
    """视频更新结果"""
    bvid: str
    view_count: int
    like_count: int
    favorite_count: int
    reply_count: int
    success: bool
    error: Optional[str] = None


class VideoUpdater:
    """视频数据更新器"""

    def __init__(
        self,
        credential: Optional[Credential] = None,
        monitor_service: Optional[MonitorPoolService] = None,
        judge_service: Optional[HotJudgeService] = None,
    ):
        self.credential = self._create_credential(credential)
        self.monitor_service = monitor_service or MonitorPoolService()
        self.judge_service = judge_service or HotJudgeService()
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

    async def _get_video_detail_async(self, bvid: str) -> Optional[Dict[str, Any]]:
        """异步获取视频详情（延时由调用方控制）"""
        try:
            v = video.Video(bvid=bvid, credential=self.credential)
            video_data = await v.get_info()

            if not video_data.get("bvid"):
                return None

            stat = video_data.get("stat", {})

            return {
                "bvid": bvid,
                "title": video_data.get("title", ""),
                "author": video_data.get("owner", {}).get("name", ""),
                "channel": video_data.get("tname", ""),
                "view_count": stat.get("view", 0),
                "like_count": stat.get("like", 0),
                "favorite_count": stat.get("favorite", 0),
                "reply_count": stat.get("reply", 0),
                "pubdate": video_data.get("pubdate", 0),
                "cover_url": video_data.get("pic", ""),
            }

        except Exception as e:
            print(f"Get video detail error: {e}")
            return None

    def get_video_detail(self, bvid: str) -> Optional[Dict[str, Any]]:
        """获取视频详情"""
        return self._sync(self._get_video_detail_async(bvid))

    def update_all_monitoring_videos(
        self,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        judge_callback: Optional[Callable[[str], None]] = None,
    ) -> dict:
        """
        更新所有监控中的视频数据（流式处理，避免内存超限）

        流程：
        1. 批量拉取最新播放写入 view_today
        2. 计算增速
        3. 执行爆款判定并更新状态
        4. 全部完成后执行 roll_views 滚动数据

        Args:
            progress_callback: 进度回调函数 callback(current, total)
            judge_callback: 判定回调函数 callback(bvid)，每判定完一个视频后调用

        Returns:
            更新结果统计 {
                "total": int,
                "success": int,
                "failed": int,
                "judged": int,
                "featured": int,
                "errors": List[str]
            }
        """
        total = self.monitor_service.count_monitoring_videos()
        success = 0
        failed = 0
        judged = 0
        featured = 0
        errors = []
        judged_bvids = []
        processed = 0

        for video in self.monitor_service.iter_all_monitoring_videos(batch_size=500):
            processed += 1
            if progress_callback:
                progress_callback(processed, total)

            try:
                result = self._update_single_video(video.bvid)
                if result["success"]:
                    success += 1
                    judged_bvids.append(video.bvid)
                else:
                    failed += 1
                    if result.get("error"):
                        errors.append(f"{video.bvid}: {result['error']}")
            except Exception as e:
                failed += 1
                errors.append(f"{video.bvid}: {str(e)}")

        for bvid in judged_bvids:
            try:
                is_featured = self.judge_service.judge_video(bvid)
                judged += 1
                if is_featured:
                    featured += 1
                if judge_callback:
                    judge_callback(bvid)
            except Exception as e:
                errors.append(f"judge {bvid}: {str(e)}")

        for bvid in judged_bvids:
            try:
                self.monitor_service.roll_views(bvid)
            except Exception as e:
                errors.append(f"roll {bvid}: {str(e)}")

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "judged": judged,
            "featured": featured,
            "errors": errors,
            "updated_at": datetime.now().isoformat(),
        }

    def update_videos_by_channel(
        self,
        channel: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> dict:
        videos = self.monitor_service.get_videos_by_channel(channel)
        total = len(videos)
        success = 0
        failed = 0
        judged = 0
        featured = 0
        errors = []
        judged_bvids = []

        for idx, video in enumerate(videos):
            if progress_callback:
                progress_callback(idx + 1, total)

            try:
                result = self._update_single_video(video.bvid)
                if result["success"]:
                    success += 1
                    judged_bvids.append(video.bvid)
                else:
                    failed += 1
                    if result.get("error"):
                        errors.append(f"{video.bvid}: {result['error']}")
            except Exception as e:
                failed += 1
                errors.append(f"{video.bvid}: {str(e)}")

        for bvid in judged_bvids:
            try:
                is_featured = self.judge_service.judge_video(bvid)
                judged += 1
                if is_featured:
                    featured += 1
            except Exception as e:
                errors.append(f"judge {bvid}: {str(e)}")

        for bvid in judged_bvids:
            try:
                self.monitor_service.roll_views(bvid)
            except Exception as e:
                errors.append(f"roll {bvid}: {str(e)}")

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "judged": judged,
            "featured": featured,
            "errors": errors,
            "channel": channel,
            "updated_at": datetime.now().isoformat(),
        }

    def _update_single_video(self, bvid: str) -> dict:
        try:
            detail = self.get_video_detail(bvid)
            if not detail:
                return {"success": False, "error": "Failed to get video detail"}

            success = self.monitor_service.update_video_views(
                bvid=bvid,
                view_today=detail["view_count"],
                like_count=detail["like_count"],
                favorite_count=detail["favorite_count"],
                reply_count=detail["reply_count"],
            )

            if not success:
                return {"success": False, "error": "Failed to update database"}

            self.monitor_service.calculate_growth_rate(bvid)

            return {"success": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def batch_update_videos(
        self,
        bvids: List[str],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> dict:
        total = len(bvids)
        success = 0
        failed = 0
        judged = 0
        featured = 0
        errors = []
        judged_bvids = []

        for idx, bvid in enumerate(bvids):
            if progress_callback:
                progress_callback(idx + 1, total)

            try:
                result = self._update_single_video(bvid)
                if result["success"]:
                    success += 1
                    judged_bvids.append(bvid)
                else:
                    failed += 1
                    if result.get("error"):
                        errors.append(f"{bvid}: {result['error']}")
            except Exception as e:
                failed += 1
                errors.append(f"{bvid}: {str(e)}")

        for bvid in judged_bvids:
            try:
                is_featured = self.judge_service.judge_video(bvid)
                judged += 1
                if is_featured:
                    featured += 1
            except Exception as e:
                errors.append(f"judge {bvid}: {str(e)}")

        for bvid in judged_bvids:
            try:
                self.monitor_service.roll_views(bvid)
            except Exception as e:
                errors.append(f"roll {bvid}: {str(e)}")

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "judged": judged,
            "featured": featured,
            "errors": errors,
            "updated_at": datetime.now().isoformat(),
        }

    def get_online_count(self, bvid: str, cid: int) -> int:
        """获取视频实时在线人数（同步方法，直接调用）"""
        import requests
        try:
            url = "https://api.bilibili.com/x/player/online/total"
            params = {"bvid": bvid, "cid": cid}
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.bilibili.com",
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            data = response.json()

            if data.get("code") == 0:
                return data.get("data", {}).get("online", 0)
            return 0
        except Exception as e:
            print(f"Get online count error: {e}")
            return 0
