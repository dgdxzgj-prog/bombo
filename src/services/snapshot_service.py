"""
视频时序快照服务
每小时采集视频全量数据，用于滑动窗口增速计算
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple, Callable, Any

from sqlalchemy import text
from bilibili_api import video
from bilibili_api.credential import Credential
from bilibili_api.exceptions import ResponseException, NetworkException

from src.utils.database import get_db_session
from src.config import settings


class SnapshotService:
    """视频时序快照服务"""

    def __init__(self, credential: Optional[Credential] = None):
        self.credential = self._create_credential(credential)

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

            # 获取视频分P的cid（取第一个分P）
            cid = 0
            pages = video_data.get("pages", [])
            if pages:
                cid = pages[0].get("cid", 0)

            return {
                "bvid": bvid,
                "view_count": stat.get("view", 0),
                "like_count": stat.get("like", 0),
                "favorite_count": stat.get("favorite", 0),
                "reply_count": stat.get("reply", 0),
                "cid": cid,
            }

        except Exception as e:
            print(f"Get video detail error: {e}")
            return None

    def get_video_detail(self, bvid: str) -> Optional[Dict[str, Any]]:
        """获取视频详情"""
        return self._sync(self._get_video_detail_async(bvid))

    def get_online_count(self, bvid: str, cid: int) -> int:
        """获取视频实时在线人数"""
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
                # B站API返回 {"total": "1000+", "count": "643"}
                # count 是数字字符串，total 可能是 "1000+" 格式
                count_str = data.get("data", {}).get("count", "0")
                try:
                    return int(count_str)
                except (ValueError, TypeError):
                    return 0
            return 0
        except Exception as e:
            print(f"Get online count error: {e}")
            return 0

    def save_snapshot(
        self,
        bvid: str,
        snapshot_time: datetime,
        view_count: int,
        like_count: int,
        favorite_count: int,
        reply_count: int,
        coin_count: int = 0,
        share_count: int = 0,
        danmu_count: int = 0,
        online_count: int = 0,
    ) -> bool:
        """
        保存视频快照数据

        Args:
            bvid: 视频bvid
            snapshot_time: 快照时间（整点时间）
            view_count: 播放量
            like_count: 点赞数
            favorite_count: 收藏数
            reply_count: 评论数
            coin_count: 投币数
            share_count: 分享数
            danmu_count: 弹幕数
            online_count: 在线人数

        Returns:
            是否保存成功
        """
        try:
            with get_db_session() as session:
                session.execute(
                    text("""
                        INSERT INTO hourly_snapshot
                        (bvid, snapshot_time, view_count, like_count, favorite_count,
                         reply_count, coin_count, share_count, danmu_count, online_count)
                        VALUES
                        (:bvid, :snapshot_time, :view_count, :like_count, :favorite_count,
                         :reply_count, :coin_count, :share_count, :danmu_count, :online_count)
                        ON CONFLICT (bvid, snapshot_time) DO UPDATE SET
                            view_count = EXCLUDED.view_count,
                            like_count = EXCLUDED.like_count,
                            favorite_count = EXCLUDED.favorite_count,
                            reply_count = EXCLUDED.reply_count,
                            coin_count = EXCLUDED.coin_count,
                            share_count = EXCLUDED.share_count,
                            danmu_count = EXCLUDED.danmu_count,
                            online_count = EXCLUDED.online_count
                    """),
                    {
                        "bvid": bvid,
                        "snapshot_time": snapshot_time,
                        "view_count": view_count,
                        "like_count": like_count,
                        "favorite_count": favorite_count,
                        "reply_count": reply_count,
                        "coin_count": coin_count,
                        "share_count": share_count,
                        "danmu_count": danmu_count,
                        "online_count": online_count,
                    }
                )
            return True
        except Exception as e:
            print(f"Failed to save snapshot for {bvid}: {e}")
            return False

    def get_snapshot(self, bvid: str, snapshot_time: datetime) -> Optional[Dict]:
        """
        获取指定时间的快照数据

        Args:
            bvid: 视频bvid
            snapshot_time: 快照时间

        Returns:
            快照数据字典，如果不存在返回None
        """
        with get_db_session() as session:
            result = session.execute(
                text("""
                    SELECT bvid, snapshot_time, view_count, like_count, favorite_count,
                           reply_count, coin_count, share_count, danmu_count, online_count
                    FROM hourly_snapshot
                    WHERE bvid = :bvid AND snapshot_time = :snapshot_time
                """),
                {"bvid": bvid, "snapshot_time": snapshot_time}
            ).fetchone()

            if result is None:
                return None

            return {
                "bvid": result[0],
                "snapshot_time": result[1],
                "view_count": result[2],
                "like_count": result[3],
                "favorite_count": result[4],
                "reply_count": result[5],
                "coin_count": result[6],
                "share_count": result[7],
                "danmu_count": result[8],
                "online_count": result[9],
            }

    def get_window_snapshot(self, bvid: str, current_time: datetime, window_hours: int = 24) -> Optional[Dict]:
        """
        获取滑动窗口起始点的快照数据

        Args:
            bvid: 视频bvid
            current_time: 当前时间
            window_hours: 窗口小时数，默认24

        Returns:
            窗口起始点快照数据，如果不存在返回None
        """
        window_start = current_time - timedelta(hours=window_hours)
        # 对齐到整点
        window_start = window_start.replace(minute=0, second=0, microsecond=0)

        return self.get_snapshot(bvid, window_start)

    def calculate_sliding_growth_rate(
        self,
        bvid: str,
        current_view_count: int,
        current_time: datetime,
        window_hours: int = 24,
    ) -> Tuple[float, bool]:
        """
        计算滑动窗口增速

        Args:
            bvid: 视频bvid
            current_view_count: 当前播放量
            current_time: 当前时间
            window_hours: 窗口小时数，默认24

        Returns:
            (growth_rate, has_complete_window)
            - growth_rate: 增速百分比
            - has_complete_window: 是否有完整的24小时窗口数据
        """
        growth_rate, has_window, _ = self.calculate_sliding_growth_rate_detail(
            bvid, current_view_count, current_time, window_hours
        )
        return growth_rate, has_window

    def calculate_sliding_growth_rate_detail(
        self,
        bvid: str,
        current_view_count: int,
        current_time: datetime,
        window_hours: int = 24,
    ) -> Tuple[float, bool, int]:
        """
        计算滑动窗口增速（详细版）

        Args:
            bvid: 视频bvid
            current_view_count: 当前播放量
            current_time: 当前时间
            window_hours: 窗口小时数，默认24

        Returns:
            (growth_rate, has_complete_window, view_24h_ago)
            - growth_rate: 增速百分比
            - has_complete_window: 是否有完整的24小时窗口数据
            - view_24h_ago: 24小时前的播放量
        """
        window_snapshot = self.get_window_snapshot(bvid, current_time, window_hours)

        if window_snapshot is None:
            return 0.0, False, 0

        view_24h_ago = window_snapshot["view_count"]
        if view_24h_ago == 0:
            return 0.0, False, 0

        # 计算增速
        growth_rate = round(
            (current_view_count - view_24h_ago) / view_24h_ago * 100,
            2
        )

        return growth_rate, True, view_24h_ago

    def get_video_age_hours(self, bvid: str, current_time: datetime) -> Optional[float]:
        """
        获取视频入库时长（小时）

        Args:
            bvid: 视频bvid
            current_time: 当前时间

        Returns:
            入库时长（小时），如果视频不存在返回None
        """
        with get_db_session() as session:
            result = session.execute(
                text("SELECT first_seen FROM monitor_pool WHERE bvid = :bvid"),
                {"bvid": bvid}
            ).fetchone()

            if result is None or result[0] is None:
                return None

            first_seen = result[0]
            age = (current_time - first_seen).total_seconds() / 3600
            return age

    def capture_current_snapshot(self, bvid: str) -> Optional[Dict]:
        """
        采集当前视频快照并保存（使用线程池执行爬虫调用）

        Args:
            bvid: 视频bvid

        Returns:
            采集的详情数据（包含view_count等），失败返回None
        """
        # 在线程池中执行同步爬虫调用，避免 event loop 冲突
        def fetch_detail():
            return self.get_video_detail(bvid)

        future = _executor.submit(fetch_detail)
        detail = future.result(timeout=30)

        if not detail:
            return None

        # 获取实时在线人数（同步方法，直接调用）
        online_count = 0
        if detail.get("cid"):
            online_count = self.get_online_count(bvid, detail["cid"])

        # 获取当前整点时间
        now = datetime.now().replace(minute=0, second=0, microsecond=0)

        self.save_snapshot(
            bvid=bvid,
            snapshot_time=now,
            view_count=detail["view_count"],
            like_count=detail["like_count"],
            favorite_count=detail["favorite_count"],
            reply_count=detail["reply_count"],
            coin_count=0,  # bilibili-api 暂不支持
            share_count=0,
            danmu_count=0,
            online_count=online_count,
        )

        return {
            "bvid": bvid,
            "view_count": detail["view_count"],
            "like_count": detail["like_count"],
            "favorite_count": detail["favorite_count"],
            "reply_count": detail["reply_count"],
            "online_count": online_count,
        }

    async def _capture_single_async(self, bvid: str, semaphore: asyncio.Semaphore) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """使用信号量限制并发采集单个视频（带随机延时防风控）"""
        import random
        async with semaphore:
            try:
                # 随机延时 1-3 秒，避免B站风控
                await asyncio.sleep(random.uniform(1, 3))

                detail = await self._get_video_detail_async(bvid)
                if not detail:
                    return (False, None, f"{bvid}: Failed to get video detail")

                # 获取在线人数
                online_count = 0
                if detail.get("cid"):
                    online_count = self.get_online_count(bvid, detail["cid"])

                # 获取当前整点时间
                now = datetime.now().replace(minute=0, second=0, microsecond=0)

                self.save_snapshot(
                    bvid=bvid,
                    snapshot_time=now,
                    view_count=detail["view_count"],
                    like_count=detail["like_count"],
                    favorite_count=detail["favorite_count"],
                    reply_count=detail["reply_count"],
                    coin_count=0,
                    share_count=0,
                    danmu_count=0,
                    online_count=online_count,
                )

                return (True, {
                    "bvid": bvid,
                    "view_count": detail["view_count"],
                    "like_count": detail["like_count"],
                    "favorite_count": detail["favorite_count"],
                    "reply_count": detail["reply_count"],
                    "online_count": online_count,
                }, None)
            except Exception as e:
                return (False, None, f"{bvid}: {str(e)}")

    def capture_all_monitoring_snapshots(
        self,
        progress_callback: Optional[callable] = None,
        on_each_capture: Optional[Callable[[Dict], None]] = None,
        batch_size: int = 100,
        concurrency: int = 10,
        status: str = "monitoring",
    ) -> Dict:
        """
        批量采集所有监控中视频的当前快照（异步并发采集）

        Args:
            progress_callback: 进度回调函数 callback(current, total)
            on_each_capture: 每个快照采集后的回调函数 callback(data)，用于边采集边处理
            batch_size: 每批处理的 bvid 数量
            concurrency: 并发数，默认10
            status: 要采集的视频状态，默认 "monitoring"，可设为 "featured" 采集爆款视频

        Returns:
            采集结果统计
        """
        # 同步入口，调用异步版本
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self._capture_all_monitoring_snapshots_async(
                progress_callback, on_each_capture, batch_size, concurrency, status
            )
        )

    async def _capture_all_monitoring_snapshots_async(
        self,
        progress_callback: Optional[callable] = None,
        on_each_capture: Optional[Callable[[Dict], None]] = None,
        batch_size: int = 100,
        concurrency: int = 10,
        status: str = "monitoring",
    ) -> Dict:
        """异步批量采集实现"""
        # 分批获取 bvids，避免一次性加载所有 bvid 到内存
        total = self._count_monitoring_videos(status)
        success = 0
        failed = 0
        errors = []
        completed = 0
        semaphore = asyncio.Semaphore(concurrency)

        for offset in range(0, total, batch_size):
            bvids = self._fetch_monitoring_bvids(limit=batch_size, offset=offset, status=status)

            # 创建所有协程
            tasks = [
                self._capture_single_async(bvid, semaphore)
                for bvid in bvids
            ]

            # 使用 gather 并发执行，带结果顺序保持
            results = await asyncio.gather(*tasks)

            for result in results:
                completed += 1
                ok, data, error = result
                if ok and data:
                    success += 1
                    if on_each_capture:
                        on_each_capture(data)
                else:
                    failed += 1
                    if error:
                        errors.append(error)

                if progress_callback:
                    progress_callback(completed, total)

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "errors": errors[:100],
            "captured_at": datetime.now().isoformat(),
        }

    def _count_monitoring_videos(self, status: str = "monitoring") -> int:
        """获取指定状态视频数量"""
        with get_db_session() as session:
            result = session.execute(
                text("SELECT COUNT(*) FROM monitor_pool WHERE status = :status"),
                {"status": status}
            ).scalar()
            return result or 0

    def _fetch_monitoring_bvids(self, limit: int = 100, offset: int = 0, status: str = "monitoring") -> List[str]:
        """分批获取指定状态的视频 bvid"""
        with get_db_session() as session:
            results = session.execute(
                text("SELECT bvid FROM monitor_pool WHERE status = :status LIMIT :limit OFFSET :offset"),
                {"limit": limit, "offset": offset, "status": status}
            ).fetchall()
            return [r[0] for r in results]