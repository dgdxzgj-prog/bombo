"""
视频相关定时任务
"""
import time
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import text
from src.utils.database import get_db_session

# ============================================
# 修复 bilibili-api Brotli 解压错误
# brotlicffi.Decompressor.decompress() 只接受1个参数
# 但 aiohttp 会传入2个参数 (data, max_length)
# ============================================
try:
    import brotlicffi
    _orig_decompress = brotlicffi.Decompressor.decompress
    def _patched_decompress(self, data, max_length=None):
        return _orig_decompress(self, data)
    brotlicffi.Decompressor.decompress = _patched_decompress
except ImportError:
    pass

from src.tasks.scheduler import get_scheduler
from src.crawlers.video_updater import VideoUpdater
from src.crawlers.video_discoverer import VideoDiscoverer
from src.crawlers.daily_hot_api import DailyHotApiClient, normalize_channel, TRACK_RID_MAP, TRACK_NAME_MAP
from src.crawlers.author_info_collector import AuthorInfoCollector
from src.services.monitor_pool_service import MonitorPoolService
from src.services.snapshot_service import SnapshotService
from src.services.hot_judge import HotJudgeService
from src.services.ai_analysis_service import get_ai_analysis_service
from src.services.track_adaptive_threshold_service import get_track_threshold_service
from src.models.video import Video, VideoStatus
from src.config import settings
from src.utils.logger import safe_str


def video_update_task() -> dict:
    """
    播放量更新任务（已废弃，请使用 hourly_video_update_task）
    保留仅用于兼容，逻辑转发到新任务
    """
    return hourly_video_update_task()


def hourly_video_update_task() -> dict:
    """
    每小时快照采集任务（P0核心任务）

    流程：
    1. 全量抓取监控池视频最新数据，写入时序快照表
    2. 边采集边同步 view_today 和 max_online_today
    3. 状态判定由 daily_video_judgment 每天06:00执行

    注意：
    - 此任务仅负责数据采集和更新
    - 不进行状态判定（爆款/衰退）
    - max_online_today 在每天06:00由 daily_video_judgment 重置

    Returns:
        任务执行结果统计
    """
    print(f"[{datetime.now().isoformat()}] Starting hourly video update task...")

    snapshot_service = SnapshotService()
    monitor_service = MonitorPoolService()

    # Step 1: 采集全量快照（边采集边同步 view_today 和 max_online_today）
    print(f"[{datetime.now().isoformat()}] Step 1: Capturing monitoring video snapshots...")

    view_today_sync_count = 0
    max_online_updated_count = 0

    def on_each_capture(data: dict) -> None:
        """每个快照采集后立即同步 view_today 和 max_online_today"""
        nonlocal view_today_sync_count, max_online_updated_count
        try:
            bvid = data["bvid"]
            online_count = data.get("online_count", 0) or 0
            author_mid = data.get("author_mid", "")

            # 更新 view_today 等基本信息
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

            # 更新 max_online_today（只增不减）
            if online_count > 0:
                monitor_service.update_max_online_today(bvid, online_count)
                max_online_updated_count += 1

            # 更新 author_mid（如果为空）
            if author_mid:
                monitor_service.update_author_mid_if_null(bvid, author_mid)

        except Exception as e:
            print(f"  Failed to sync data for {data['bvid']}: {e}")

    def progress_callback(current: int, total: int) -> None:
        if current % 50 == 0 or current == total:
            print(f"[{datetime.now().isoformat()}] Snapshot progress: {current}/{total}")

    snapshot_result = snapshot_service.capture_all_monitoring_snapshots(
        progress_callback=progress_callback,
        on_each_capture=on_each_capture,
        batch_size=100,
        status="",  # 不区分状态，采集所有视频
    )
    print(f"  Monitoring snapshots: total={snapshot_result['total']}, success={snapshot_result['success']}, failed={snapshot_result['failed']}")
    print(f"  view_today synced: {view_today_sync_count} videos")
    print(f"  max_online_today updated: {max_online_updated_count} videos")

    result = {
        "snapshot": snapshot_result,
        "view_today_sync": view_today_sync_count,
        "max_online_updated": max_online_updated_count,
        "executed_at": datetime.now().isoformat(),
    }

    print(f"[{datetime.now().isoformat()}] Hourly update task completed:")
    print(f"  Total snapshots: {snapshot_result['success']}/{snapshot_result['total']}")
    print(f"  view_today synced: {view_today_sync_count} videos")
    print(f"  max_online_today updated: {max_online_updated_count} videos")
    print(f"  Status judgment is handled by daily_video_judgment (06:00)")

    return result


def video_discovery_task(keywords: Optional[list] = None) -> dict:
    """
    新视频发现任务
    每6小时执行一次
    根据关键词搜索新视频并入库
    """
    # 如果没有提供关键词，使用配置的关键词
    if keywords is None:
        # 从数据库获取各赛道的关键词
        keywords = _get_keywords_from_config()

    discoverer = VideoDiscoverer()

    def progress_callback(keyword: str, current: int, total: int) -> None:
        """进度回调"""
        print(f"[{datetime.now().isoformat()}] Discovering '{keyword}': {current}/{total}")

    video_generator = discoverer.discover_multi_keywords(
        keywords,
        max_pages_per_keyword=5,
        progress_callback=progress_callback,
    )

    # 流式保存发现的视频（边发现边保存，避免内存超限）
    success, skip, error, discovered = discoverer.save_discovered_videos_streaming(video_generator)

    result = {
        "keywords_count": len(keywords),
        "discovered": discovered,
        "saved": success,
        "skipped": skip,
        "errors": error,
        "executed_at": datetime.now().isoformat(),
    }

    print(f"[{datetime.now().isoformat()}] Video discovery completed:")
    print(f"  Keywords: {result['keywords_count']}")
    print(f"  Discovered: {result['discovered']}")
    print(f"  Saved: {result['saved']}")
    print(f"  Skipped: {result['skipped']}")
    print(f"  Errors: {result['errors']}")

    return result


def _get_keywords_from_config() -> list:
    """
    从配置获取搜索关键词
    实际应从数据库读取各赛道的关键词配置
    """
    # 默认关键词
    default_keywords = [
        "搞笑",
        "美食",
        "游戏",
        "科技",
        "音乐",
        "舞蹈",
        "生活",
        "知识",
        "影视",
        "动物",
    ]
    return default_keywords


def daily_hot_video_task() -> dict:
    """
    每日热榜视频采集任务
    每小时执行一次
    从B站热榜获取视频并入库
    """
    client = DailyHotApiClient()
    monitor_service = MonitorPoolService()
    discoverer = VideoDiscoverer()

    saved_count = 0
    skip_count = 0
    error_count = 0

    # 获取热门视频（多个页面）
    print(f"[{datetime.now().isoformat()}] Fetching daily hot videos...")

    # 获取热门视频
    all_videos = []
    for page in range(1, 4):  # 获取前3页热门视频
        videos = client.get_popular_videos(page=page, page_size=20)
        if not videos:
            break
        all_videos.extend(videos)
        print(f"  Page {page}: got {len(videos)} videos")

    print(f"[{datetime.now().isoformat()}] Total hot videos fetched: {len(all_videos)}")

    # 转换为Video对象并入库
    for hot_video in all_videos:
        try:
            # 检查是否已存在
            existing = monitor_service.get_video_by_bvid(hot_video.bvid)
            if existing:
                skip_count += 1
                continue

            # 使用VideoDiscoverer获取作者MID
            detail = discoverer.get_video_detail(hot_video.bvid)
            author_mid = detail.author_mid if detail else ""

            # 转换为Video对象
            pubdate = None
            if hot_video.pubdate:
                pubdate = datetime.fromtimestamp(hot_video.pubdate)

            video = Video(
                bvid=hot_video.bvid,
                title=hot_video.title,
                author=hot_video.author,
                author_mid=author_mid or None,
                channel=normalize_channel(hot_video.tname) if hot_video.tname else "生活",
                keyword="热榜",
                view_yesterday=0,
                view_today=hot_video.play,
                growth_rate=0.0,
                like_count=hot_video.like,
                favorite_count=hot_video.favorite,
                reply_count=hot_video.reply,
                pubdate=pubdate,
                cover_url=hot_video.pic,
                duration=hot_video.duration or 0,
                tags=hot_video.tags,
                status=VideoStatus.FEATURED,
            )

            monitor_service.add_video(video)
            # 同时写入video_channel表（热榜视频直接标记为爆款）
            monitor_service.add_video_channel_with_status(video.bvid, video.channel, "featured")

            # 设置UP主信息采集标记（异步采集）
            if video.author_mid:
                monitor_service.set_need_author_collect(video.bvid)

            saved_count += 1
            print(f"  Added: {hot_video.bvid} - {safe_str(hot_video.title, 30)}")

        except ValueError:
            # 重复视频
            skip_count += 1
        except Exception as e:
            error_count += 1
            print(f"  Error adding {hot_video.bvid}: {e}")

    result = {
        "total_fetched": len(all_videos),
        "saved": saved_count,
        "skipped": skip_count,
        "errors": error_count,
        "executed_at": datetime.now().isoformat(),
    }

    print(f"[{datetime.now().isoformat()}] Daily hot task completed:")
    print(f"  Fetched: {result['total_fetched']}")
    print(f"  Saved: {result['saved']}")
    print(f"  Skipped: {result['skipped']}")
    print(f"  Errors: {result['errors']}")

    return result


def ai_analyze_featured_task() -> dict:
    """
    AI分析视频任务
    对监控池中所有还没有AI分析记录的视频进行AI分析
    分析封面和内容两个维度
    如果视频没有封面则跳过封面分析

    注意：此任务应在hourly_video_update完成后执行
    每次最多分析3个视频，避免API rate limit问题
    """
    # 检查是否启用 AI 分析
    if not settings.ENABLE_AI_ANALYSIS:
        print(f"[{datetime.now().isoformat()}] AI analysis disabled, skipping task...")
        return {"status": "skipped", "reason": "AI analysis disabled"}

    print(f"[{datetime.now().isoformat()}] Starting AI analysis task...")

    ai_service = get_ai_analysis_service()

    # 从monitor_pool获取还没有AI分析记录的视频
    # 使用LEFT JOIN ai_cache找到没有分析记录的视频
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
                LEFT JOIN ai_cache ac ON mp.bvid = ac.bvid
                WHERE ac.bvid IS NULL
                ORDER BY mp.view_today DESC
                LIMIT 3
            """)
        ).fetchall()

    # 转换为Video对象
    videos = []
    for row in results:
        video = Video(
            id=row[0],
            bvid=row[1],
            title=row[2],
            author=row[3],
            channel=row[4],
            keyword=row[5],
            view_yesterday=row[6],
            view_today=row[7],
            growth_rate=row[8] or 0.0,
            like_count=row[9] or 0,
            favorite_count=row[10] or 0,
            reply_count=row[11] or 0,
            coin_count=row[12] or 0,
            share_count=row[13] or 0,
            danmu_count=row[14] or 0,
            online_count=row[15],
            max_online_today=row[16],
            pubdate=row[17],
            cover_url=row[18],
            first_seen=row[19],
            last_collected=row[20],
            created_at=row[21],
            updated_at=row[22],
        )
        videos.append(video)

    print(f"[{datetime.now().isoformat()}] Found {len(videos)} videos without AI analysis")

    # 先尝试从缓存获取已分析的视频
    analyzed_count = 0
    skipped_count = 0
    error_count = 0

    for video in videos:
        try:
            # 决定分析类型
            analysis_type = "content"  # 至少分析内容
            if video.cover_url:
                analysis_type = "both"  # 有封面则分析封面+内容

            # 执行AI分析
            result = ai_service.analyze_video(
                video,
                cover_url=video.cover_url,
                analysis_type=analysis_type,
            )

            if result:
                # 缓存分析结果
                ai_service.cache_analysis(result, title=video.title, cover_url=video.cover_url)
                analyzed_count += 1
                print(f"  Analyzed: {video.bvid} - {safe_str(video.title, 30)}")
            else:
                error_count += 1
                print(f"  Failed: {video.bvid} - {safe_str(video.title, 30)}")

            # 每次分析完成后等待10秒，避免API过载
            time.sleep(10)

        except Exception as e:
            error_count += 1
            print(f"  Error analyzing {video.bvid}: {e}")

    result = {
        "total": len(videos),
        "analyzed": analyzed_count,
        "skipped": skipped_count,
        "errors": error_count,
        "executed_at": datetime.now().isoformat(),
    }

    print(f"[{datetime.now().isoformat()}] AI analysis task completed:")
    print(f"  Total: {result['total']}")
    print(f"  Analyzed: {result['analyzed']}")
    print(f"  Skipped (cached): {result['skipped']}")
    print(f"  Errors: {result['errors']}")

    return result


def author_collection_task() -> dict:
    """
    UP主信息异步采集任务
    每小时执行一次
    从监控池中获取需要采集UP主信息的视频，进行异步采集
    使用数据库锁确保只有一个进程执行采集，避免触发B站风控
    """
    import socket
    import uuid

    # 生成唯一锁持有者标识（主机名+进程ID+随机UUID）
    lock_holder = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"

    print(f"[{datetime.now().isoformat()}] Starting author collection task (lock_holder={lock_holder})...")

    monitor_service = MonitorPoolService()

    # 尝试获取分布式锁
    if not monitor_service.acquire_author_collect_lock(lock_holder):
        print(f"[{datetime.now().isoformat()}] Could not acquire author_collect_lock, another process is running. Skipping.")
        return {
            "status": "skipped",
            "reason": "lock_not_acquired",
            "lock_holder": lock_holder,
            "executed_at": datetime.now().isoformat(),
        }

    print(f"[{datetime.now().isoformat()}] Lock acquired, starting author collection...")

    try:
        author_collector = AuthorInfoCollector()
        collected_count = 0
        failed_count = 0
        skipped_count = 0
        processed_bvids = []

        # 迭代获取需要采集的视频
        for video in monitor_service.iter_videos_need_author_collect(batch_size=50):
            try:
                if not video.author_mid:
                    # 没有UP主MID，跳过
                    skipped_count += 1
                    processed_bvids.append(video.bvid)
                    continue

                # 采集UP主信息
                author = author_collector.collect_and_save(video.author_mid)
                if author:
                    collected_count += 1
                    print(f"  Collected: {video.author_mid} - {author.name} (fans: {author.fans})")
                else:
                    failed_count += 1
                    print(f"  Failed: {video.bvid} - {video.author_mid}")

                processed_bvids.append(video.bvid)

            except Exception as e:
                failed_count += 1
                print(f"  Error collecting author for {video.bvid}: {e}")
                processed_bvids.append(video.bvid)

        # 批量重置采集标记
        if processed_bvids:
            reset_count = monitor_service.reset_need_author_collect_batch(processed_bvids)
            print(f"[{datetime.now().isoformat()}] Reset need_author_collect for {reset_count} videos")

        result = {
            "status": "success",
            "collected": collected_count,
            "failed": failed_count,
            "skipped": skipped_count,
            "processed": len(processed_bvids),
            "lock_holder": lock_holder,
            "executed_at": datetime.now().isoformat(),
        }

        print(f"[{datetime.now().isoformat()}] Author collection task completed:")
        print(f"  Collected: {result['collected']}")
        print(f"  Failed: {result['failed']}")
        print(f"  Skipped: {result['skipped']}")
        print(f"  Processed: {result['processed']}")

        return result

    finally:
        # 释放锁
        monitor_service.release_author_collect_lock(lock_holder)
        print(f"[{datetime.now().isoformat()}] Lock released for {lock_holder}")


def daily_track_threshold_task() -> dict:
    """
    每日赛道阈值计算任务
    每天凌晨01:00执行一次
    遍历所有赛道，计算每个赛道的T_up和T_down阈值
    """
    print(f"[{datetime.now().isoformat()}] Starting daily track threshold calculation...")

    threshold_service = get_track_threshold_service()
    results = threshold_service.calculate_all_thresholds()

    result = {
        "tracks_updated": len(results),
        "results": results,
        "executed_at": datetime.now().isoformat(),
    }

    print(f"[{datetime.now().isoformat()}] Track threshold calculation completed:")
    print(f"  Tracks updated: {result['tracks_updated']}")

    return result


def daily_video_judgment_task() -> dict:
    """
    每日视频状态判定任务
    每天06:00执行一次
    遍历所有处于monitor/hit状态的视频，执行爆款判定
    规则：
    - 爆款状态：max_online_today >= T_up → 升级爆款
    - hit状态：max_online_today < T_down → 降级衰退
    - 视频入库小于24小时不参与判定
    - 判定完成后重置max_online_today为0
    """
    print(f"[{datetime.now().isoformat()}] Starting daily video judgment...")

    monitor_service = MonitorPoolService()
    threshold_service = get_track_threshold_service()

    now = datetime.now()
    upgraded_count = 0
    demoted_count = 0
    skipped_cold_start = 0
    skipped_no_threshold = 0
    reset_count = 0

    # 获取所有活跃赛道
    tracks = threshold_service.get_all_active_tracks()

    for track in tracks:
        channel_id = track["channel_id"]
        t_up = track["t_up"]
        t_down = track["t_down"]

        if t_up == 0 or t_down == 0:
            print(f"  [{channel_id}] No valid threshold, skipping")
            skipped_no_threshold += 1
            continue

        # 获取该赛道下所有处于monitoring或featured状态的视频
        with get_db_session() as session:
            results = session.execute(
                text("""
                    SELECT mp.bvid, mp.max_online_today, mp.first_featured_at,
                           vc.status as channel_status
                    FROM monitor_pool mp
                    JOIN video_channel vc ON mp.bvid = vc.video_bvid
                    WHERE vc.channel_id = :channel_id
                      AND vc.status IN ('monitoring', 'featured')
                """),
                {"channel_id": channel_id}
            ).fetchall()

        for row in results:
            bvid = row[0]
            max_online_today = row[1] or 0
            first_featured_at = row[2]
            current_status = row[3]

            # 检查是否冷启动（入库/上榜小于24小时）
            if first_featured_at:
                age_hours = (now - first_featured_at).total_seconds() / 3600
                if age_hours < 24:
                    skipped_cold_start += 1
                    # 重置max_online_today但不改变状态
                    monitor_service.update_video_max_online_today(bvid, 0)
                    continue

            # 执行判定
            if current_status == "monitoring":
                # 监控中 → 爆款判定
                if max_online_today >= t_up:
                    monitor_service.update_video_channel_status(bvid, channel_id, VideoStatus.FEATURED)
                    # 记录首次上榜时间
                    monitor_service.update_video_first_featured_at(bvid, now)
                    upgraded_count += 1
                    print(f"  [{channel_id}] {bvid}: monitoring → featured (max_online={max_online_today}, t_up={t_up})")
            elif current_status == "featured":
                # 爆款 → 衰退判定
                if max_online_today < t_down:
                    monitor_service.update_video_channel_status(bvid, channel_id, VideoStatus.DECLINED)
                    demoted_count += 1
                    print(f"  [{channel_id}] {bvid}: featured → declined (max_online={max_online_today}, t_down={t_down})")

            # 重置max_online_today
            monitor_service.update_video_max_online_today(bvid, 0)
            reset_count += 1

    result = {
        "upgraded": upgraded_count,
        "demoted": demoted_count,
        "skipped_cold_start": skipped_cold_start,
        "skipped_no_threshold": skipped_no_threshold,
        "reset_max_online": reset_count,
        "executed_at": datetime.now().isoformat(),
    }

    print(f"[{datetime.now().isoformat()}] Daily video judgment completed:")
    print(f"  Upgraded (monitoring→featured): {upgraded_count}")
    print(f"  Demoted (featured→declined): {demoted_count}")
    print(f"  Skipped (cold start <24h): {skipped_cold_start}")
    print(f"  Skipped (no threshold): {skipped_no_threshold}")
    print(f"  Reset max_online_today: {reset_count}")

    return result


def video_cleanup_task() -> dict:
    """
    视频清理任务
    在 daily_video_judgment 完成后执行（每天06:30）
    清理逻辑：
    1. 入库超过3天
    2. 不在任何赛道的爆款视频中（video_channel中status != 'featured'）
    3. 移入历史表，从监控池删除
    """
    print(f"[{datetime.now().isoformat()}] Starting video cleanup task...")

    monitor_service = MonitorPoolService()
    now = datetime.now()

    # 查询需要清理的视频：入库超过3天且不在任何赛道的featured状态
    with get_db_session() as session:
        results = session.execute(
            text("""
                SELECT mp.id, mp.bvid, mp.title, mp.author, mp.author_mid, mp.channel, mp.keyword,
                       mp.view_yesterday, mp.view_today, mp.growth_rate,
                       mp.like_count, mp.favorite_count, mp.reply_count,
                       mp.coin_count, mp.share_count, mp.danmu_count,
                       mp.online_count, mp.max_online_today,
                       mp.pubdate, mp.cover_url, mp.status,
                       mp.first_seen, mp.last_collected, mp.created_at, mp.updated_at,
                       mp.first_featured_at, mp.max_online_ever
                FROM monitor_pool mp
                WHERE mp.first_seen < :cutoff_time
                  AND NOT EXISTS (
                      SELECT 1 FROM video_channel vc WHERE vc.video_bvid = mp.bvid AND vc.status = 'featured'
                  )
                LIMIT 500
            """),
            {"cutoff_time": now - timedelta(days=3)}
        ).fetchall()

    archived_count = 0
    error_count = 0

    for row in results:
        try:
            bvid = row[1]

            # 获取该视频最后的赛道状态信息
            with get_db_session() as session:
                last_vc = session.execute(
                    text("""
                        SELECT vc.channel_id, cc.channel_name, vc.status
                        FROM video_channel vc
                        JOIN channel_config cc ON vc.channel_id = cc.channel_id
                        WHERE vc.video_bvid = :bvid
                        ORDER BY vc.is_primary DESC, vc.id DESC
                        LIMIT 1
                    """),
                    {"bvid": bvid}
                ).fetchone()

            last_channel = last_vc[1] if last_vc else ""
            last_status = last_vc[2] if last_vc else "unknown"

            # 插入历史表
            with get_db_session() as session:
                session.execute(
                    text("""
                        INSERT INTO video_history (
                            bvid, title, author, author_mid, channel, keyword,
                            view_yesterday, view_today, growth_rate,
                            like_count, favorite_count, reply_count,
                            coin_count, share_count, danmu_count,
                            online_count, max_online_today,
                            pubdate, cover_url, status,
                            first_seen, last_collected, created_at, updated_at,
                            first_featured_at, max_online_ever,
                            archived_at, archived_reason, last_status, last_channel
                        ) VALUES (
                            :bvid, :title, :author, :author_mid, :channel, :keyword,
                            :view_yesterday, :view_today, :growth_rate,
                            :like_count, :favorite_count, :reply_count,
                            :coin_count, :share_count, :danmu_count,
                            :online_count, :max_online_today,
                            :pubdate, :cover_url, :status,
                            :first_seen, :last_collected, :created_at, :updated_at,
                            :first_featured_at, :max_online_ever,
                            :archived_at, :archived_reason, :last_status, :last_channel
                        )
                    """),
                    {
                        "bvid": row[1],
                        "title": row[2],
                        "author": row[3],
                        "author_mid": row[4],
                        "channel": row[5],
                        "keyword": row[6],
                        "view_yesterday": row[7],
                        "view_today": row[8],
                        "growth_rate": row[9],
                        "like_count": row[10],
                        "favorite_count": row[11],
                        "reply_count": row[12],
                        "coin_count": row[13],
                        "share_count": row[14],
                        "danmu_count": row[15],
                        "online_count": row[16],
                        "max_online_today": row[17],
                        "pubdate": row[18],
                        "cover_url": row[19],
                        "status": row[20],
                        "first_seen": row[21],
                        "last_collected": row[22],
                        "created_at": row[23],
                        "updated_at": row[24],
                        "first_featured_at": row[25],
                        "max_online_ever": row[26],
                        "archived_at": now,
                        "archived_reason": "cleanup",
                        "last_status": last_status,
                        "last_channel": last_channel,
                    }
                )

                # 从监控池删除
                session.execute(
                    text("DELETE FROM monitor_pool WHERE bvid = :bvid"),
                    {"bvid": bvid}
                )

                # 从video_channel删除
                session.execute(
                    text("DELETE FROM video_channel WHERE video_bvid = :bvid"),
                    {"bvid": bvid}
                )

            archived_count += 1
            print(f"  Archived: {bvid} - {row[2][:30] if row[2] else 'N/A'}")

        except Exception as e:
            error_count += 1
            print(f"  Error archiving {row[1]}: {e}")

    result = {
        "archived": archived_count,
        "errors": error_count,
        "executed_at": now.isoformat(),
    }

    print(f"[{datetime.now().isoformat()}] Video cleanup task completed:")
    print(f"  Archived: {result['archived']}")
    print(f"  Errors: {result['errors']}")

    return result


def region_ranking_task() -> dict:
    """
    全站热榜视频采集任务
    每6小时执行一次
    从B站全站热榜(rid=0, day=3)获取视频并入库
    根据pid_name_v2进行赛道匹配
    新视频直接写入featured状态
    """
    from src.crawlers.daily_hot_api import normalize_channel

    client = DailyHotApiClient()
    monitor_service = MonitorPoolService()
    discoverer = VideoDiscoverer()

    saved_count = 0
    skip_count = 0
    error_count = 0

    print(f"[{datetime.now().isoformat()}] Starting region ranking task...")

    try:
        # 获取全站热榜视频（rid=0, day=3）
        videos = client.get_region_ranking(limit=50)
        print(f"[{datetime.now().isoformat()}] Fetched {len(videos)} videos from ranking API")
    except Exception as e:
        print(f"  Failed to fetch ranking: {e}")
        videos = []

    for hot_video in videos:
        try:
            # 检查是否已存在
            existing = monitor_service.get_video_by_bvid(hot_video.bvid)
            if existing:
                skip_count += 1
                continue

            # 根据pid_name_v2匹配赛道
            channel_name = normalize_channel(hot_video.tname, hot_video.pid_name_v2)

            # 使用VideoDiscoverer获取作者MID
            detail = discoverer.get_video_detail(hot_video.bvid)
            author_mid = detail.author_mid if detail else ""

            # 转换为Video对象
            pubdate = None
            if hot_video.pubdate:
                pubdate = datetime.fromtimestamp(hot_video.pubdate)

            # 新视频直接写入featured状态
            video = Video(
                bvid=hot_video.bvid,
                title=hot_video.title,
                author=hot_video.author,
                author_mid=author_mid or None,
                channel=channel_name,
                keyword="全站热榜",
                view_yesterday=0,
                view_today=hot_video.play,
                growth_rate=0.0,
                like_count=hot_video.like,
                favorite_count=hot_video.favorite,
                reply_count=hot_video.reply,
                pubdate=pubdate,
                cover_url=hot_video.pic,
                status=VideoStatus.FEATURED,
            )

            monitor_service.add_video(video)
            # 写入video_channel表，状态为featured（爆款）
            monitor_service.add_video_channel_with_status(
                video.bvid,
                channel_name,
                "featured"
            )

            saved_count += 1
            print(f"  Added: [{channel_name}] {hot_video.bvid} - {safe_str(hot_video.title, 30)}")

        except ValueError:
            # 重复视频
            skip_count += 1
        except Exception as e:
            error_count += 1
            print(f"  Error adding {hot_video.bvid}: {e}")

        # 避免请求过快
        time.sleep(0.5)

    result = {
        "total_fetched": len(videos),
        "saved": saved_count,
        "skipped": skip_count,
        "errors": error_count,
        "executed_at": datetime.now().isoformat(),
    }

    print(f"[{datetime.now().isoformat()}] Region ranking task completed:")
    print(f"  Total fetched: {result['total_fetched']}")
    print(f"  Saved: {result['saved']}")
    print(f"  Skipped: {result['skipped']}")
    print(f"  Errors: {result['errors']}")

    return result


def init_video_tasks() -> None:
    """
    初始化视频相关定时任务
    将任务注册到调度器

    执行顺序：
    1. region_ranking（每6小时） - 分区热榜采集
    2. video_discovery（每6小时）
    3. daily_hot（每小时）
    4. hourly_video_update（每小时）
    5. ai_analyze_featured（每小时）
    """
    scheduler = get_scheduler()

    # 全站热榜任务 - 每6小时
    # 从B站全站热榜(rid=0, day=3)获取视频，根据pid_name_v2匹配赛道
    # 新视频直接入库为爆款状态
    scheduler.add_interval_task(
        task_id="region_ranking",
        name="Region Ranking",
        func=region_ranking_task,
        interval_seconds=6 * 3600,  # 6小时
    )

    # 新视频发现任务 - 每6小时（已暂停）
    # scheduler.add_interval_task(
    #     task_id="video_discovery",
    #     name="Video Discovery",
    #     func=video_discovery_task,
    #     interval_seconds=6 * 3600,  # 6小时
    # )

    # 每日热榜任务 - 每小时（入库通道）
    scheduler.add_interval_task(
        task_id="daily_hot",
        name="Daily Hot Videos",
        func=daily_hot_video_task,
        interval_seconds=3600,  # 1小时
    )

    # 每小时统一调度任务（P0核心任务）
    # 包含：快照采集 + 成熟视频判定 + 状态更新
    # 执行时间：每小时执行一次，延迟5分钟启动
    scheduler.add_interval_task(
        task_id="hourly_video_update",
        name="Hourly Video Update",
        func=hourly_video_update_task,
        interval_seconds=3600,  # 1小时
    )

    # AI分析爆款视频任务 - 每小时执行一次
    # 在hourly_video_update完成后执行，确保分析的是最新状态
    # 延迟10分钟启动，确保在hourly_video_update之后
    scheduler.add_interval_task(
        task_id="ai_analyze_featured",
        name="AI Analyze Featured Videos",
        func=ai_analyze_featured_task,
        interval_seconds=3600,  # 1小时
    )

    # UP主信息异步采集任务 - 每小时执行一次
    # 使用数据库锁确保只有一个进程执行采集
    # 在hourly_video_update完成后执行（:25）
    # [已暂停] - 2026-07-24
    # scheduler.add_cron_task(
    #     task_id="author_collection",
    #     name="Author Collection",
    #     func=author_collection_task,
    #     hour=0,
    #     minute=25,
    # )

    # 每日赛道阈值计算任务 - 每天凌晨01:00执行
    # 计算所有赛道的T_up和T_down阈值
    scheduler.add_cron_task(
        task_id="daily_track_threshold",
        name="Daily Track Threshold",
        func=daily_track_threshold_task,
        hour=1,
        minute=0,
    )

    # 每日视频状态判定任务 - 每天06:00执行
    # 遍历所有视频执行爆款判定
    scheduler.add_cron_task(
        task_id="daily_video_judgment",
        name="Daily Video Judgment",
        func=daily_video_judgment_task,
        hour=6,
        minute=0,
    )

    # 视频清理任务 - 每天06:30执行
    # 在daily_video_judgment完成后执行，清理入库超过3天且不在任何赛道爆款中的视频
    scheduler.add_cron_task(
        task_id="video_cleanup",
        name="Video Cleanup",
        func=video_cleanup_task,
        hour=6,
        minute=30,
    )

    # 重新调度分时执行任务，避免同时执行
    # region_ranking: 启动时立即执行一次（采集热榜视频入库为爆款）
    # daily_hot: 立即执行（热点采集）
    # hourly_video_update: 延迟5分钟执行（视频数据更新）
    # ai_analyze_featured: 延迟10分钟执行（AI分析）
    scheduler._schedule_task(scheduler.tasks["region_ranking"], initial_delay=0)
    scheduler._schedule_task(scheduler.tasks["daily_hot"], initial_delay=0)
    scheduler._schedule_task(scheduler.tasks["hourly_video_update"], initial_delay=300)
    scheduler._schedule_task(scheduler.tasks["ai_analyze_featured"], initial_delay=600)
