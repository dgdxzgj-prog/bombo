"""
视频相关定时任务
"""
from datetime import datetime
from typing import Optional

from src.tasks.scheduler import get_scheduler
from src.crawlers.video_updater import VideoUpdater
from src.crawlers.video_discoverer import VideoDiscoverer
from src.crawlers.daily_hot_api import DailyHotApiClient, normalize_channel
from src.services.monitor_pool_service import MonitorPoolService
from src.services.snapshot_service import SnapshotService
from src.services.hot_judge import HotJudgeService
from src.services.ai_analysis_service import get_ai_analysis_service
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
    每小时统一调度任务（P0新任务）

    流程：
    0. 前置清洗：强制将入库<24h的featured视频降级为monitoring
    1. 全量抓取监控池视频最新数据，写入时序快照表（边采集边同步view_today）
    2. 对入库>=24h视频计算滑动24h真实增速、执行judge爆款判定、更新上榜状态
    3. 对入库<24h视频（冷启动）跳过判定，不更新状态

    Returns:
        任务执行结果统计
    """
    print(f"[{datetime.now().isoformat()}] Starting hourly video update task...")

    snapshot_service = SnapshotService()
    judge_service = HotJudgeService()
    monitor_service = MonitorPoolService()

    # Step 0: 前置清洗 - 强制降级冷启动视频（暂时禁用）
    # print(f"[{datetime.now().isoformat()}] Step 0: Pre-cleanup cold start featured videos...")
    #
    # now = datetime.now()
    # cold_start_demoted = 0
    #
    # # 查询所有 featured 状态的视频（分批获取，避免内存超限）
    # for video in monitor_service.iter_videos_by_status(VideoStatus.FEATURED, batch_size=500):
    #     if video.first_seen:
    #         age_hours = (now - video.first_seen).total_seconds() / 3600
    #         if age_hours < 24:
    #             # 冷启动视频强制降级为 monitoring
    #             monitor_service.update_video_status(video.bvid, VideoStatus.MONITORING)
    #             cold_start_demoted += 1
    #             print(f"  Demoted cold start: {video.bvid} ({safe_str(video.title, 30)}) age={age_hours:.1f}h")
    #
    # print(f"  Cold start featured demoted: {cold_start_demoted}")

    cold_start_demoted = 0  # 暂时禁用

    # Step 1: 采集全量快照（边采集边同步 view_today，避免内存超限）
    print(f"[{datetime.now().isoformat()}] Step 1: Capturing snapshots with streaming view_today sync...")

    view_today_sync_count = 0

    def on_each_capture(data: dict) -> None:
        """每个快照采集后立即同步 view_today"""
        nonlocal view_today_sync_count
        try:
            monitor_service.update_video_views(
                bvid=data["bvid"],
                view_today=data["view_count"],
                like_count=data.get("like_count"),
                favorite_count=data.get("favorite_count"),
                reply_count=data.get("reply_count"),
            )
            view_today_sync_count += 1
        except Exception as e:
            print(f"  Failed to sync view_today for {data['bvid']}: {e}")

    def progress_callback(current: int, total: int) -> None:
        if current % 50 == 0 or current == total:
            print(f"[{datetime.now().isoformat()}] Snapshot progress: {current}/{total}")

    snapshot_result = snapshot_service.capture_all_monitoring_snapshots(
        progress_callback=progress_callback,
        on_each_capture=on_each_capture,
        batch_size=100,
    )
    print(f"  Monitoring snapshots: total={snapshot_result['total']}, success={snapshot_result['success']}, failed={snapshot_result['failed']}")
    print(f"  view_today synced (streaming): {view_today_sync_count} videos")

    # Step 1.5: 采集爆款视频快照（获取在线人数）
    print(f"[{datetime.now().isoformat()}] Step 1.5: Capturing featured video snapshots...")

    featured_online_count = 0

    def on_featured_capture(data: dict) -> None:
        """每个爆款视频快照采集后更新 online_count"""
        nonlocal featured_online_count
        try:
            monitor_service.update_video_views(
                bvid=data["bvid"],
                view_today=data["view_count"],
                like_count=data.get("like_count"),
                favorite_count=data.get("favorite_count"),
                reply_count=data.get("reply_count"),
            )
            # 在线人数已保存在快照表中，无需额外处理
            featured_online_count += 1
        except Exception as e:
            print(f"  Failed to sync featured video {data['bvid']}: {e}")

    def featured_progress_callback(current: int, total: int) -> None:
        if current % 10 == 0 or current == total:
            print(f"[{datetime.now().isoformat()}] Featured snapshot progress: {current}/{total}")

    featured_result = snapshot_service.capture_all_monitoring_snapshots(
        progress_callback=featured_progress_callback,
        on_each_capture=on_featured_capture,
        batch_size=100,
        status="featured",
    )
    print(f"  Featured snapshots: total={featured_result['total']}, success={featured_result['success']}, failed={featured_result['failed']}")

    # Step 2: 批量判定成熟视频
    print(f"[{datetime.now().isoformat()}] Step 2: Judging mature videos...")

    # 获取入库>=24h的成熟视频（流式处理）
    now = datetime.now()
    mature_bvids = []

    for video in monitor_service.iter_videos_by_status(VideoStatus.MONITORING, batch_size=500):
        if video.first_seen:
            age_hours = (now - video.first_seen).total_seconds() / 3600
            if age_hours >= 24:
                mature_bvids.append(video.bvid)

    print(f"  Found {len(mature_bvids)} mature videos (>=24h)")

    # 对成熟视频执行判定（正向：标记通过的视频；逆向：降级不通过的视频）
    featured_count = 0
    demoted_count = 0
    judged_count = 0

    for bvid in mature_bvids:
        try:
            # 获取视频当前状态
            video = monitor_service.get_video_by_bvid(bvid)
            current_status = video.status if video else None

            # 执行爆款判定
            is_hot, reason = judge_service.is_hot_video(bvid)

            if is_hot:
                # 正向：判定通过，维持/更新为featured
                if current_status != VideoStatus.FEATURED:
                    monitor_service.update_video_status(bvid, VideoStatus.FEATURED)
                featured_count += 1
            else:
                # 逆向：判定不通过，且当前状态为featured → 降级为monitoring
                if current_status == VideoStatus.FEATURED:
                    monitor_service.update_video_status(bvid, VideoStatus.MONITORING)
                    demoted_count += 1

            judged_count += 1
        except Exception as e:
            print(f"  Error judging {bvid}: {e}")

    print(f"  Judged: {judged_count}, Featured: {featured_count}, Demoted: {demoted_count}")

    # Step 3: 冷启动视频（<24h）统计
    cold_start_count = snapshot_result['total'] - len(mature_bvids)
    print(f"  Cold start videos (<24h): {cold_start_count} - skipped")

    result = {
        "snapshot": snapshot_result,
        "featured_snapshot": featured_result,
        "view_today_sync": view_today_sync_count,
        "cold_start_demoted": cold_start_demoted,
        "mature_videos": len(mature_bvids),
        "judged": judged_count,
        "featured_new": featured_count,
        "demoted": demoted_count,
        "cold_start_skipped": cold_start_count,
        "executed_at": datetime.now().isoformat(),
    }

    print(f"[{datetime.now().isoformat()}] Hourly update task completed:")
    print(f"  Monitoring snapshots: {snapshot_result['success']}/{snapshot_result['total']}")
    print(f"  Featured snapshots: {featured_result['success']}/{featured_result['total']}")
    print(f"  view_today synced: {view_today_sync_count} videos")
    print(f"  Cold start featured demoted: {cold_start_demoted}")
    print(f"  Mature judged: {judged_count}, Featured: {featured_count}, Demoted: {demoted_count}")
    print(f"  Cold start skipped: {cold_start_count}")

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

            # 转换为Video对象
            pubdate = None
            if hot_video.pubdate:
                pubdate = datetime.fromtimestamp(hot_video.pubdate)

            video = Video(
                bvid=hot_video.bvid,
                title=hot_video.title,
                author=hot_video.author,
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
                status=VideoStatus.FEATURED,
            )

            monitor_service.add_video(video)
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
    AI分析爆款视频任务
    对已上榜(featured状态)的视频进行AI分析
    分析封面和内容两个维度
    如果视频没有封面则跳过封面分析
    """
    print(f"[{datetime.now().isoformat()}] Starting AI analysis task...")

    monitor_service = MonitorPoolService()
    ai_service = get_ai_analysis_service()

    # 获取所有已上榜视频
    featured_videos = monitor_service.get_videos_by_status(VideoStatus.FEATURED, limit=1000)

    print(f"[{datetime.now().isoformat()}] Found {len(featured_videos)} featured videos")

    # 先尝试从缓存获取已分析的视频
    analyzed_count = 0
    skipped_count = 0
    error_count = 0

    for video in featured_videos:
        try:
            # 尝试获取缓存的分析结果
            cached = ai_service.get_cached_analysis(video.bvid)
            if cached:
                # 检查缓存是否完整
                cover_missing = cached.cover_analysis is None and video.cover_url
                content_missing = cached.content_analysis is None
                if not cover_missing and not content_missing:
                    skipped_count += 1
                    continue

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
                ai_service.cache_analysis(result)
                analyzed_count += 1
                print(f"  Analyzed: {video.bvid} - {safe_str(video.title, 30)}")
            else:
                error_count += 1

        except Exception as e:
            error_count += 1
            print(f"  Error analyzing {video.bvid}: {e}")

    result = {
        "total": len(featured_videos),
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


def init_video_tasks() -> None:
    """
    初始化视频相关定时任务
    将任务注册到调度器

    执行顺序（每小时）：
    1. video_discovery（每6小时，如有到时则优先执行）
    2. daily_hot
    3. hourly_video_update
    4. ai_analyze_featured
    """
    scheduler = get_scheduler()

    # 新视频发现任务 - 每6小时（优先级最高，如有到时则优先执行）
    scheduler.add_interval_task(
        task_id="video_discovery",
        name="Video Discovery",
        func=video_discovery_task,
        interval_seconds=6 * 3600,  # 6小时
    )

    # 每日热榜任务 - 每小时（入库通道）
    scheduler.add_interval_task(
        task_id="daily_hot",
        name="Daily Hot Videos",
        func=daily_hot_video_task,
        interval_seconds=3600,  # 1小时
    )

    # 每小时统一调度任务（P0核心任务）
    # 包含：快照采集 + 成熟视频判定 + 状态更新
    scheduler.add_interval_task(
        task_id="hourly_video_update",
        name="Hourly Video Update",
        func=hourly_video_update_task,
        interval_seconds=3600,  # 1小时
    )

    # AI分析爆款视频任务 - 每小时执行一次
    scheduler.add_interval_task(
        task_id="ai_analyze_featured",
        name="AI Analyze Featured Videos",
        func=ai_analyze_featured_task,
        interval_seconds=3600,  # 1小时
    )
