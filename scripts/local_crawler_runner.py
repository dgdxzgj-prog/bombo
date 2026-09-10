"""
本地运行的独立爬虫任务程序

运行以下任务：
1. hourly_video_update - 每小时快照采集（带反爬策略）
2. daily_keyword_refresh - 每日关键词刷新
3. daily_featured_settlement - 每日上榜结算
4. hourly_user_feed_update - 每小时用户订阅更新（带反爬策略）

使用方法：
    python scripts/local_crawler_runner.py [task_name]

示例：
    python scripts/local_crawler_runner.py           # 运行所有任务
    python scripts/local_crawler_runner.py hourly    # 只运行小时级任务
    python scripts/local_crawler_runner.py daily     # 只运行日级任务
"""
import sys
import os
import time
import random
import argparse
from datetime import datetime

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置环境变量（如果需要）
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# 云数据库配置（Supabase PostgreSQL）
os.environ["DATABASE_URL"] = "postgresql+psycopg2://postgres.ryklhtuzrsdgcjbkqqyn:J_9Nag7%24%26n%21f%26dz@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres?sslmode=require"

# Brotli解压patch（修复aiohttp兼容性问题）
try:
    import brotlicffi
    _orig_decompress = brotlicffi.Decompressor.decompress
    def _patched_decompress(self, data, max_length=None):
        return _orig_decompress(self, data)
    brotlicffi.Decompressor.decompress = _patched_decompress
except ImportError:
    pass


def safe_print(msg: str) -> None:
    """安全打印，支持中文"""
    try:
        print(msg)
    except Exception:
        # 尝试转义无法编码的字符
        print(msg.encode("utf-8", errors="replace").decode("utf-8", errors="replace"))


def hourly_video_update() -> dict:
    """
    小时级任务1: 快照采集
    从 monitor_pool 采集所有视频的快照数据
    """
    from src.services.snapshot_service import SnapshotService
    from src.services.monitor_pool_service import MonitorPoolService

    safe_print(f"[{datetime.now().isoformat()}] Starting hourly_video_update...")

    snapshot_service = SnapshotService()
    monitor_service = MonitorPoolService()

    view_today_sync_count = 0
    max_online_updated_count = 0

    def on_each_capture(data: dict) -> None:
        nonlocal view_today_sync_count, max_online_updated_count
        try:
            bvid = data["bvid"]
            online_count = data.get("online_count", 0) or 0
            author_mid = data.get("author_mid", "")

            monitor_service.update_video_views(
                bvid=bvid,
                view_today=data["view_count"],
                like_count=data.get("like_count"),
                favorite_count=data.get("favorite_count"),
                reply_count=data.get("reply_count"),
                coin_count=data.get("coin_count"),
                share_count=data.get("share_count"),
                danmu_count=data.get("danmu_count"),
                online_count=online_count,
            )
            view_today_sync_count += 1

            if online_count > 0:
                monitor_service.update_max_online_today(bvid, online_count)
                max_online_updated_count += 1

            if author_mid:
                monitor_service.update_author_mid_if_null(bvid, author_mid)

        except Exception as e:
            safe_print(f"  Failed to sync data for {data['bvid']}: {e}")

    def progress_callback(current: int, total: int) -> None:
        if current % 50 == 0 or current == total:
            safe_print(f"[{datetime.now().isoformat()}] Snapshot progress: {current}/{total}")

    snapshot_result = snapshot_service.capture_all_monitoring_snapshots(
        progress_callback=progress_callback,
        on_each_capture=on_each_capture,
        batch_size=100,
        status="",  # 不区分状态，采集所有视频
    )

    safe_print(f"  Monitoring snapshots: total={snapshot_result['total']}, success={snapshot_result['success']}, failed={snapshot_result['failed']}")
    safe_print(f"  view_today synced: {view_today_sync_count} videos")
    safe_print(f"  max_online_today updated: {max_online_updated_count} videos")

    return {
        "snapshot": snapshot_result,
        "view_today_sync": view_today_sync_count,
        "max_online_updated": max_online_updated_count,
    }


def daily_keyword_refresh() -> dict:
    """
    日级任务1: 每日关键词刷新
    清理衰退视频 + 刷新搜索关键词
    """
    from src.tasks.user_feed_tasks import daily_keyword_refresh_task

    safe_print(f"[{datetime.now().isoformat()}] Starting daily_keyword_refresh...")
    result = daily_keyword_refresh_task()
    safe_print(f"  Result: {result}")
    return result


def daily_featured_settlement() -> dict:
    """
    日级任务2: 每日上榜结算
    根据 max_online_today 判定上榜/下榜
    """
    from src.tasks.user_feed_tasks import daily_featured_settlement_task

    safe_print(f"[{datetime.now().isoformat()}] Starting daily_featured_settlement...")
    result = daily_featured_settlement_task()
    safe_print(f"  Result: {result}")
    return result


def hourly_user_feed_update() -> dict:
    """
    小时级任务2: 用户订阅视频更新
    更新 user_monitor_pool 中所有视频的播放数据和在线人数
    """
    import asyncio
    from src.services.user_monitor_service import UserMonitorService
    from src.crawlers.anti_crawler import get_anti_crawler
    from bilibili_api import video as bilibili_video, Credential
    from src.config import settings

    safe_print(f"[{datetime.now().isoformat()}] Starting hourly_user_feed_update...")

    def _create_credential():
        if settings.BILI_COOKIE:
            cookie_dict = {}
            for item in settings.BILI_COOKIE.split(";"):
                item = item.strip()
                if "=" in item:
                    key, value = item.split("=", 1)
                    cookie_dict[key.strip()] = value.strip()
            return Credential(
                sessdata=cookie_dict.get("SESSDATA"),
                bili_jct=cookie_dict.get("bili_jct"),
                buvid3=cookie_dict.get("BUVID3")
            )
        return Credential()

    async def _get_video_detail_with_retry(bvid: str, credential: Credential, max_retries: int = 3):
        """带重试机制的视频详情获取（处理412错误）"""
        import httpx

        base_delay = 2
        for attempt in range(max_retries):
            try:
                v = bilibili_video.Video(bvid=bvid, credential=credential)
                detail = await v.get_info()
                if detail and detail.get("bvid"):
                    return detail
                return None
            except Exception as e:
                error_str = str(e)
                is_412 = (
                    "412" in error_str or
                    "status code 412" in error_str.lower() or
                    isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 412
                )

                if is_412 and attempt < max_retries - 1:
                    delay = min(base_delay * (2 ** attempt) + random.uniform(0.5, 2), 30)
                    safe_print(f"  412 error for {bvid}, retry {attempt + 1}/{max_retries}, waiting {delay:.2f}s")
                    await asyncio.sleep(delay)
                    continue

                return None
        return None

    async def _do_update():
        monitor_service = UserMonitorService()
        credential = _create_credential()
        anti_crawler = get_anti_crawler()

        updated_count = 0
        error_count = 0

        for video in monitor_service.iter_all_monitoring_videos(limit=5000, batch_size=100):
            try:
                # 随机延时 2-5 秒，避免B站风控
                await asyncio.sleep(random.uniform(2, 5))

                # 获取视频最新数据（带重试）
                detail = await _get_video_detail_with_retry(video.bvid, credential)
                if not detail:
                    error_count += 1
                    continue

                stat = detail.get("stat", {})
                view_count = stat.get("view", 0)

                # 获取在线人数
                online_count = 0
                try:
                    cid = detail.get("pages", [{}])[0].get("cid", 0) if detail.get("pages") else 0
                    if cid:
                        online_api = f"https://api.bilibili.com/x/player/online/total?bvid={video.bvid}&cid={cid}"
                        import requests
                        resp = requests.get(online_api, headers=anti_crawler.get_headers(), timeout=10)
                        data = resp.json()
                        if data.get("code") == 0:
                            online_count = int(data.get("data", {}).get("total", 0) or data.get("data", {}).get("online", 0))
                except Exception:
                    pass

                # 更新统计数据
                monitor_service.update_video_stats(
                    bvid=video.bvid,
                    view_today=view_count,
                    like_count=stat.get("like", 0),
                    favorite_count=stat.get("favorite", 0),
                    reply_count=stat.get("reply", 0),
                    coin_count=stat.get("coin", 0),
                    share_count=stat.get("share", 0),
                    danmu_count=stat.get("danmaku", 0),
                    online_count=online_count,
                )

                # 更新最大在线人数（只增不减）
                if online_count > 0:
                    monitor_service.update_max_online_today(video.bvid, online_count)

                updated_count += 1

            except Exception as e:
                error_count += 1
                safe_print(f"  Error processing {video.bvid}: {e}")
                continue

        return {
            "updated_count": updated_count,
            "error_count": error_count,
        }

    return asyncio.run(_do_update())


def run_hourly_tasks():
    """运行小时级任务"""
    safe_print("=" * 60)
    safe_print(f"[{datetime.now().isoformat()}] Running HOURLY tasks...")
    safe_print("=" * 60)

    # 任务1: 快照采集
    safe_print("\n[1/2] Running hourly_video_update...")
    result1 = hourly_video_update()
    safe_print(f"  Completed: {result1}")

    # 任务间延时
    safe_print("\n  Waiting 60 seconds before next task...")
    time.sleep(60)

    # 任务2: 用户订阅更新
    safe_print("\n[2/2] Running hourly_user_feed_update...")
    result2 = hourly_user_feed_update()
    safe_print(f"  Completed: {result2}")

    return {"hourly_video_update": result1, "hourly_user_feed_update": result2}


def run_daily_tasks():
    """运行日级任务"""
    safe_print("=" * 60)
    safe_print(f"[{datetime.now().isoformat()}] Running DAILY tasks...")
    safe_print("=" * 60)

    # 任务1: 关键词刷新
    safe_print("\n[1/2] Running daily_keyword_refresh...")
    result1 = daily_keyword_refresh()
    safe_print(f"  Completed: {result1}")

    # 任务间延时
    safe_print("\n  Waiting 30 seconds before next task...")
    time.sleep(30)

    # 任务2: 上榜结算
    safe_print("\n[2/2] Running daily_featured_settlement...")
    result2 = daily_featured_settlement()
    safe_print(f"  Completed: {result2}")

    return {"daily_keyword_refresh": result1, "daily_featured_settlement": result2}


def run_all_tasks():
    """运行所有任务"""
    safe_print("=" * 60)
    safe_print(f"[{datetime.now().isoformat()}] Running ALL local tasks...")
    safe_print("=" * 60)

    results = {}

    # 运行小时级任务
    results.update(run_hourly_tasks())

    safe_print("\n" + "=" * 60)
    safe_print(f"[{datetime.now().isoformat()}] All tasks completed!")
    safe_print("=" * 60)

    return results


def main():
    parser = argparse.ArgumentParser(description="本地爬虫任务运行器")
    parser.add_argument(
        "task_type",
        nargs="?",
        default="all",
        choices=["all", "hourly", "daily"],
        help="任务类型: all(全部), hourly(小时级), daily(日级)"
    )
    args = parser.parse_args()

    if args.task_type == "hourly":
        run_hourly_tasks()
    elif args.task_type == "daily":
        run_daily_tasks()
    else:
        run_all_tasks()


if __name__ == "__main__":
    main()
