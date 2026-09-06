"""
用户自选赛道定时任务
"""
import asyncio
import random
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict

# Brotli解压patch（修复aiohttp兼容性问题）
try:
    import brotlicffi
    _orig_decompress = brotlicffi.Decompressor.decompress
    def _patched_decompress(self, data, max_length=None):
        return _orig_decompress(self, data)
    brotlicffi.Decompressor.decompress = _patched_decompress
except ImportError:
    pass

from bilibili_api import video as bilibili_video, Credential

from src.config import settings
from src.models.user_monitor_video import UserMonitorVideo, UserVideoStatus
from src.services.user_monitor_service import UserMonitorService
from src.services.user_keyword_service import UserKeywordService
from src.services.user_feed_service import UserFeedService
from src.crawlers.anti_crawler import get_anti_crawler
from src.crawlers.daily_hot_api import normalize_channel
from src.utils.logger import safe_print


# 可配置参数
SEARCH_PLAY_THRESHOLD = 3000   # 初筛最低播放量
SEARCH_LIKE_THRESHOLD = 100    # 初筛最低点赞数
FEATURED_ONLINE_THRESHOLD = 30 # 上榜在线人数阈值
DECLINE_INCREMENT_THRESHOLD = 1000  # 24小时播放增量衰退阈值
GRACE_PERIOD_HOURS = 24        # 新视频观察期


def _create_credential() -> Credential:
    """创建认证凭证"""
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


def search_keyword_and_collect(user_id: str, keyword: str) -> int:
    """
    根据关键词搜索B站并采集视频
    返回采集到的视频数量
    """
    try:
        from bilibili_api import search as bilibili_search
    except ImportError:
        safe_print(f"[UserFeed] bilibili_api search module not available")
        return 0

    credential = _create_credential()
    monitor_service = UserMonitorService()
    feed_service = UserFeedService()
    anti_crawler = get_anti_crawler()

    safe_print(f"[UserFeed] Searching keyword: {keyword}")

    async def _do_search_and_collect():
        # 调用B站搜索API（async函数）
        search_result = await bilibili_search.search_by_type(
            keyword=keyword,
            search_type=bilibili_search.SearchObjectType.VIDEO,
            page=1,
            page_size=50
        )

        results = search_result.get("result", [])
        if not results:
            safe_print(f"[UserFeed] No results for keyword: {keyword}")
            return 0

        collected = 0
        for item in results:
            try:
                bvid = item.get("bvid")
                title = item.get("title", "").replace("<em>", "").replace("</em>", "")
                author = item.get("author", "")
                view_count = item.get("play", 0) or 0
                like_count = item.get("like", 0) or 0
                pubdate_ts = item.get("pubdate", 0)

                # 初筛条件
                if view_count < SEARCH_PLAY_THRESHOLD or like_count < SEARCH_LIKE_THRESHOLD:
                    continue

                # 获取视频详情（async）
                v = bilibili_video.Video(bvid=bvid, credential=credential)
                detail = await v.get_info()

                stat = detail.get("stat", {})
                video_detail = {
                    "title": detail.get("title", title),
                    "author": detail.get("owner", {}).get("name", author),
                    "author_mid": str(detail.get("owner", {}).get("mid", "")),
                    "channel": normalize_channel(detail.get("tname", "")),
                    "view_count": stat.get("view", 0),
                    "like_count": stat.get("like", 0),
                    "favorite_count": stat.get("favorite", 0),
                    "reply_count": stat.get("reply", 0),
                    "coin_count": stat.get("coin", 0),
                    "share_count": stat.get("share", 0),
                    "danmu_count": stat.get("danmaku", 0),
                    "pubdate": datetime.fromtimestamp(detail.get("pubdate", 0)) if detail.get("pubdate") else None,
                    "cover_url": detail.get("pic", ""),
                    "duration": detail.get("duration", 0),
                    "tags": [tag["tag_name"] for tag in detail.get("tags", [])],
                }

                # 入库 user_monitor_pool
                video_obj = UserMonitorVideo(
                    bvid=bvid,
                    keyword=keyword,
                    title=video_detail["title"],
                    author=video_detail["author"],
                    author_mid=video_detail["author_mid"],
                    channel=video_detail["channel"],
                    view_today=video_detail["view_count"],
                    like_count=video_detail["like_count"],
                    favorite_count=video_detail["favorite_count"],
                    reply_count=video_detail["reply_count"],
                    coin_count=video_detail["coin_count"],
                    share_count=video_detail["share_count"],
                    danmu_count=video_detail["danmu_count"],
                    pubdate=video_detail["pubdate"],
                    cover_url=video_detail["cover_url"],
                    duration=video_detail["duration"],
                    tags=video_detail["tags"],
                    status=UserVideoStatus.MONITORING,
                )

                monitor_service.add_video(video_obj)

                # 建立订阅关系
                feed_service.subscribe_video(user_id, bvid, keyword)

                # 获取初始在线人数
                try:
                    cid = detail.get("pages", [{}])[0].get("cid", 0) if detail.get("pages") else 0
                    if cid:
                        online_api = f"https://api.bilibili.com/x/player/online/total?bvid={bvid}&cid={cid}"
                        import requests
                        resp = requests.get(online_api, headers=anti_crawler.get_headers(), timeout=10)
                        data = resp.json()
                        if data.get("code") == 0:
                            online_count = int(data.get("data", {}).get("total", 0) or data.get("data", {}).get("online", 0))
                            monitor_service.update_max_online_today(bvid, online_count)
                except Exception:
                    pass

                collected += 1

                # 延时
                await asyncio.sleep(random.uniform(1.0, 2.0))

            except Exception as e:
                safe_print(f"[UserFeed] Error processing video: {e}")
                continue

        safe_print(f"[UserFeed] Keyword '{keyword}' collected {collected} videos")
        return collected

    try:
        return asyncio.run(_do_search_and_collect())
    except Exception as e:
        safe_print(f"[UserFeed] Search error for '{keyword}': {e}")
        return 0


def refresh_user_keywords(user_id: str, keywords: List[str]) -> int:
    """
    刷新用户的所有关键词（每日凌晨2点执行）
    返回采集到的新视频数量
    """
    total_collected = 0

    for keyword in keywords:
        try:
            collected = search_keyword_and_collect(user_id, keyword)
            total_collected += collected
        except Exception as e:
            safe_print(f"[UserFeed] Error refreshing keyword '{keyword}': {e}")
            continue

        # 关键词之间延时
        time.sleep(random.uniform(2.0, 4.0))

    safe_print(f"[UserFeed] Refresh completed. Total collected: {total_collected}")
    return total_collected


def daily_keyword_refresh_task() -> dict:
    """
    每日关键词刷新任务（凌晨2点执行）
    合并执行：衰退清理 + 刷新搜索

    优化：相同关键词只搜索一次，然后为所有订阅该关键词的用户创建订阅关系
    """
    safe_print(f"[{datetime.now().isoformat()}] Starting daily keyword refresh task...")

    # Step 1: 衰退清理
    cleanup_result = daily_video_cleanup_task()
    safe_print(f"[{datetime.now().isoformat()}] Cleanup completed: {cleanup_result}")

    # Step 2: 确保 video_keywords 表存在
    feed_service = UserFeedService()
    feed_service.ensure_video_keywords_table()

    # Step 3: 获取所有活跃关键词（去重）
    with __import__("src.utils.database", fromlist=["get_db_session"]).get_db_session() as session:
        from sqlalchemy import text

        # 获取所有唯一的关键词（去重）
        unique_keywords = session.execute(
            text("SELECT DISTINCT keyword FROM user_keywords WHERE status = 1")
        ).fetchall()
        unique_keywords = [row[0] for row in unique_keywords]

        # 获取所有用户及其关键词的映射
        user_keyword_results = session.execute(
            text("""
                SELECT DISTINCT user_id, keyword
                FROM user_keywords
                WHERE status = 1
            """)
        ).fetchall()

    # 构建 关键词 -> 用户列表 的映射
    keyword_users_map: Dict[str, List[str]] = {}
    for row in user_keyword_results:
        user_id, keyword = row[0], row[1]
        if keyword not in keyword_users_map:
            keyword_users_map[keyword] = []
        keyword_users_map[keyword].append(str(user_id))

    # Step 4: 对每个唯一关键词只搜索一次
    total_collected = 0
    total_subscribed = 0

    for keyword in unique_keywords:
        try:
            result = search_keyword_and_collect_for_all_users(keyword, keyword_users_map.get(keyword, []))
            if result:
                total_collected += result.get("videos_found", 0)
                total_subscribed += result.get("subscriptions_created", 0)
        except Exception as e:
            safe_print(f"[UserFeed] Error refreshing keyword '{keyword}': {e}")
            continue

        # 关键词之间延时
        time.sleep(random.uniform(2.0, 4.0))

    safe_print(f"[{datetime.now().isoformat()}] Daily keyword refresh completed. Videos found: {total_collected}, Subscriptions created: {total_subscribed}")

    return {
        "cleanup": cleanup_result,
        "total_collected": total_collected,
        "total_subscribed": total_subscribed,
    }


def search_keyword_and_collect_for_all_users(keyword: str, user_ids: List[str]) -> dict:
    """
    根据关键词搜索B站并为所有订阅该关键词的用户采集视频
    返回: {"videos_found": int, "subscriptions_created": int}
    """
    try:
        from bilibili_api import search as bilibili_search
    except ImportError:
        safe_print(f"[UserFeed] bilibili_api search module not available")
        return {"videos_found": 0, "subscriptions_created": 0}

    if not user_ids:
        safe_print(f"[UserFeed] No users subscribed to keyword: {keyword}")
        return {"videos_found": 0, "subscriptions_created": 0}

    credential = _create_credential()
    monitor_service = UserMonitorService()
    feed_service = UserFeedService()
    anti_crawler = get_anti_crawler()

    safe_print(f"[UserFeed] Searching keyword: {keyword} for {len(user_ids)} users")

    async def _do_search_and_collect():
        # 调用B站搜索API（async函数）
        search_result = await bilibili_search.search_by_type(
            keyword=keyword,
            search_type=bilibili_search.SearchObjectType.VIDEO,
            page=1,
            page_size=50
        )

        results = search_result.get("result", [])
        if not results:
            safe_print(f"[UserFeed] No results for keyword: {keyword}")
            return {"videos_found": 0, "subscriptions_created": 0}

        videos_found = 0
        subscriptions_created = 0

        for item in results:
            try:
                bvid = item.get("bvid")
                title = item.get("title", "").replace("<em>", "").replace("</em>", "")
                author = item.get("author", "")
                view_count = item.get("play", 0) or 0
                like_count = item.get("like", 0) or 0
                pubdate_ts = item.get("pubdate", 0)

                # 初筛条件
                if view_count < SEARCH_PLAY_THRESHOLD or like_count < SEARCH_LIKE_THRESHOLD:
                    continue

                # 获取视频详情（async）
                v = bilibili_video.Video(bvid=bvid, credential=credential)
                detail = await v.get_info()

                stat = detail.get("stat", {})
                video_detail = {
                    "title": detail.get("title", title),
                    "author": detail.get("owner", {}).get("name", author),
                    "author_mid": str(detail.get("owner", {}).get("mid", "")),
                    "channel": normalize_channel(detail.get("tname", "")),
                    "view_count": stat.get("view", 0),
                    "like_count": stat.get("like", 0),
                    "favorite_count": stat.get("favorite", 0),
                    "reply_count": stat.get("reply", 0),
                    "coin_count": stat.get("coin", 0),
                    "share_count": stat.get("share", 0),
                    "danmu_count": stat.get("danmaku", 0),
                    "pubdate": datetime.fromtimestamp(detail.get("pubdate", 0)) if detail.get("pubdate") else None,
                    "cover_url": detail.get("pic", ""),
                    "duration": detail.get("duration", 0),
                    "tags": [tag["tag_name"] for tag in detail.get("tags", [])],
                }

                # 入库 user_monitor_pool（如果已存在则更新）
                video_obj = UserMonitorVideo(
                    bvid=bvid,
                    keyword=keyword,  # 使用当前搜索的关键词
                    title=video_detail["title"],
                    author=video_detail["author"],
                    author_mid=video_detail["author_mid"],
                    channel=video_detail["channel"],
                    view_today=video_detail["view_count"],
                    like_count=video_detail["like_count"],
                    favorite_count=video_detail["favorite_count"],
                    reply_count=video_detail["reply_count"],
                    coin_count=video_detail["coin_count"],
                    share_count=video_detail["share_count"],
                    danmu_count=video_detail["danmu_count"],
                    pubdate=video_detail["pubdate"],
                    cover_url=video_detail["cover_url"],
                    duration=video_detail["duration"],
                    tags=video_detail["tags"],
                    status=UserVideoStatus.MONITORING,
                )

                monitor_service.add_video(video_obj)

                # 为所有订阅该关键词的用户创建订阅关系
                sub_count = feed_service.batch_subscribe_videos_for_users(bvid, keyword, user_ids)
                subscriptions_created += sub_count

                # 记录视频-关键词关联（用于分析）
                feed_service.batch_add_video_keywords(bvid, keyword, user_ids)

                # 获取初始在线人数
                try:
                    cid = detail.get("pages", [{}])[0].get("cid", 0) if detail.get("pages") else 0
                    if cid:
                        online_api = f"https://api.bilibili.com/x/player/online/total?bvid={bvid}&cid={cid}"
                        import requests
                        resp = requests.get(online_api, headers=anti_crawler.get_headers(), timeout=10)
                        data = resp.json()
                        if data.get("code") == 0:
                            online_count = int(data.get("data", {}).get("total", 0) or data.get("data", {}).get("online", 0))
                            monitor_service.update_max_online_today(bvid, online_count)
                except Exception:
                    pass

                videos_found += 1

                # 延时
                await asyncio.sleep(random.uniform(1.0, 2.0))

            except Exception as e:
                safe_print(f"[UserFeed] Error processing video: {e}")
                continue

        safe_print(f"[UserFeed] Keyword '{keyword}' found {videos_found} videos, created {subscriptions_created} subscriptions")
        return {"videos_found": videos_found, "subscriptions_created": subscriptions_created}

    try:
        return asyncio.run(_do_search_and_collect())
    except Exception as e:
        safe_print(f"[UserFeed] Search error for '{keyword}': {e}")
        return {"videos_found": 0, "subscriptions_created": 0}


def daily_video_cleanup_task() -> dict:
    """
    每日视频衰退清理任务
    清理条件：入库>24h 且 播放增量<1000 且 状态为monitoring
    """
    safe_print(f"[{datetime.now().isoformat()}] Starting daily video cleanup task...")

    monitor_service = UserMonitorService()
    feed_service = UserFeedService()

    now = datetime.now()
    cleaned_count = 0
    declined_bvids = []

    for video in monitor_service.iter_all_monitoring_videos(limit=10000, batch_size=100):
        try:
            # 检查是否满足清理条件
            age_hours = (now - video.first_seen).total_seconds() / 3600 if video.first_seen else 0

            # 豁免条件：新视频观察期内
            if age_hours < GRACE_PERIOD_HOURS:
                continue

            # 豁免条件：已上榜视频不清理
            if video.status == UserVideoStatus.FEATURED:
                continue

            # 计算播放增量
            play_increment = video.view_today - video.view_yesterday

            # 清理条件：播放增量 < 阈值
            if play_increment < DECLINE_INCREMENT_THRESHOLD:
                declined_bvids.append(video.bvid)

        except Exception as e:
            safe_print(f"[UserFeed] Error checking video {video.bvid}: {e}")
            continue

    # 批量标记为衰退
    if declined_bvids:
        reason = f"24小时播放增量 < {DECLINE_INCREMENT_THRESHOLD}"
        cleaned_count = monitor_service.batch_update_declined(declined_bvids, reason)

        # 解除这些视频的所有订阅关系
        for bvid in declined_bvids:
            feed_service.unsubscribe_video(user_id="system", bvid=bvid)

    safe_print(f"[{datetime.now().isoformat()}] Cleanup completed. {cleaned_count} videos declined")

    return {
        "cleaned_count": cleaned_count,
        "declined_bvids": declined_bvids[:100],  # 限制返回数量
    }


def daily_featured_settlement_task() -> dict:
    """
    每日上榜结算任务（23:59执行）
    根据当日max_online_today判定上榜/下榜
    """
    safe_print(f"[{datetime.now().isoformat()}] Starting daily featured settlement task...")

    monitor_service = UserMonitorService()
    now = datetime.now()

    featured_count = 0
    demoted_count = 0

    # 遍历所有监控中和已上榜的视频
    for video in monitor_service.iter_all_monitoring_videos(limit=10000, batch_size=100):
        try:
            max_online = video.max_online_today

            if video.status == UserVideoStatus.MONITORING:
                # 监控中 → 上榜
                if max_online > FEATURED_ONLINE_THRESHOLD:
                    monitor_service.update_video_status(
                        video.bvid,
                        UserVideoStatus.FEATURED,
                        featured_at=now
                    )
                    featured_count += 1
                    safe_print(f"[Settlement] {video.bvid} featured (max_online={max_online})")

            elif video.status == UserVideoStatus.FEATURED:
                # 已上榜 → 下榜或保持
                if max_online <= FEATURED_ONLINE_THRESHOLD:
                    monitor_service.update_video_status(
                        video.bvid,
                        UserVideoStatus.MONITORING,
                        declined_at=None,  # 不记录为衰退，只是下榜
                        declined_reason=None
                    )
                    demoted_count += 1
                    safe_print(f"[Settlement] {video.bvid} demoted (max_online={max_online})")
                else:
                    # 保持上榜，更新featured_at
                    monitor_service.update_video_status(
                        video.bvid,
                        UserVideoStatus.FEATURED,
                        featured_at=now
                    )

        except Exception as e:
            safe_print(f"[Settlement] Error processing {video.bvid}: {e}")
            continue

    safe_print(f"[{datetime.now().isoformat()}] Settlement completed. Featured: {featured_count}, Demoted: {demoted_count}")

    return {
        "featured_count": featured_count,
        "demoted_count": demoted_count,
    }


def hourly_user_feed_update_task() -> dict:
    """
    每小时更新用户订阅视频的在线人数和播放数据
    """
    async def _do_update():
        safe_print(f"[{datetime.now().isoformat()}] Starting hourly user feed update...")

        monitor_service = UserMonitorService()
        credential = _create_credential()
        anti_crawler = get_anti_crawler()

        updated_count = 0
        error_count = 0

        for video in monitor_service.iter_all_monitoring_videos(limit=5000, batch_size=100):
            try:
                # 获取视频最新数据（async）
                v = bilibili_video.Video(bvid=video.bvid, credential=credential)
                detail = await v.get_info()

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

                # 更新统计数据（包含在线人数）
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

                # 延时
                await asyncio.sleep(random.uniform(0.5, 1.5))

            except Exception as e:
                error_count += 1
                continue

        safe_print(f"[{datetime.now().isoformat()}] Hourly update completed. Updated: {updated_count}, Errors: {error_count}")

        return {
            "updated_count": updated_count,
            "error_count": error_count,
        }

    return asyncio.run(_do_update())
