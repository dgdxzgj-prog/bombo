"""
API路由
提供RESTful API端点
"""
import asyncio
import requests
from datetime import datetime
from typing import Optional, List
from functools import wraps
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException, Header, Query, Body, Response

from pydantic import BaseModel

from src.models.user import User, UserRole, UserLevel
from src.models.video import Video, VideoStatus
from src.models.channel import ChannelConfig
from src.services.auth_service import get_auth_service
from src.services.monitor_pool_service import MonitorPoolService
from src.services.channel_config_service import ChannelConfigService
from src.services.hot_judge import HotJudgeService
from src.services.ai_analysis_service import get_ai_analysis_service
from src.services.permission_service import get_permission_service
from src.services.subscription_service import get_subscription_service
from src.models.ai_analysis import AIAnalysisResult
from src.crawlers.video_updater import VideoUpdater


# 线程池用于执行同步爬虫调用
_executor = ThreadPoolExecutor(max_workers=4)


# ============== Request/Response Models ==============

class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str


class TokenResponse(BaseModel):
    token: str
    user: dict
    expires_at: str


class VideoResponse(BaseModel):
    bvid: str
    title: str
    author: str
    channel: str
    view_today: int
    growth_rate: float
    status: str


class ChannelResponse(BaseModel):
    channel_id: str
    channel_name: str
    burst_growth_threshold: float
    burst_volume_threshold: int
    is_locked: bool


class HotJudgeRequest(BaseModel):
    bvid: str


class HotJudgeResponse(BaseModel):
    is_hot: bool
    reason: str
    score: Optional[float] = None


class AddVideoRequest(BaseModel):
    """手动新增视频请求"""
    bvid: str


class AddVideoResponse(BaseModel):
    """手动新增视频响应"""
    success: bool
    message: str
    video: Optional[dict] = None


class CalibrateRequest(BaseModel):
    channel_id: str


class AIFeatureResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


# ============== Helper Functions ==============

def get_current_user(authorization: str = Header(None)) -> Optional[User]:
    """从Authorization头获取当前用户"""
    if not authorization:
        return None

    token = authorization.replace("Bearer ", "")
    auth_service = get_auth_service()
    session = auth_service.verify_token(token)

    if not session:
        return None

    return User(
        id=session.user_id,
        username=session.username,
        role=session.role,
    )


def require_auth(func):
    """需要认证的装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        user = kwargs.get("current_user")
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return func(*args, **kwargs)
    return wrapper


def require_permission(permission: str):
    """需要特定权限的装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get("current_user")
            if not user:
                raise HTTPException(status_code=401, detail="Unauthorized")
            if not user.has_permission(permission):
                raise HTTPException(status_code=403, detail="Forbidden")
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ============== API Routers ==============

# 认证路由
auth_router = APIRouter(prefix="/api/auth", tags=["认证"])


@auth_router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """用户登录"""
    auth_service = get_auth_service()
    user = auth_service.authenticate(request.username, request.password)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = auth_service.generate_token(user)

    return TokenResponse(
        token=token,
        user=user.to_dict(),
        expires_at=str(datetime.now().timestamp() + auth_service.TOKEN_EXPIRE_HOURS * 3600),
    )


@auth_router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest):
    """用户注册"""
    auth_service = get_auth_service()

    # 检查用户名是否已存在
    existing_users = auth_service.get_all_users()
    if any(u.username == request.username for u in existing_users):
        raise HTTPException(status_code=400, detail="Username already exists")

    # 第一个注册的用户设为VIP，后续用户为FREE
    role = UserRole.VIP if len(existing_users) == 0 else UserRole.FREE

    user = auth_service.register_user(
        username=request.username,
        password=request.password,
        email=request.email,
        role=role,
    )

    if not user:
        raise HTTPException(status_code=400, detail="Username already exists")

    token = auth_service.generate_token(user)

    return TokenResponse(
        token=token,
        user=user.to_dict(),
        expires_at=str(datetime.now().timestamp() + auth_service.TOKEN_EXPIRE_HOURS * 3600),
    )


@auth_router.post("/logout")
async def logout(authorization: str = Header(None)):
    """用户登出"""
    if authorization:
        token = authorization.replace("Bearer ", "")
        auth_service = get_auth_service()
        auth_service.revoke_token(token)

    return {"success": True}


@auth_router.get("/me")
async def get_current_user_info(authorization: str = Header(None)):
    """获取当前用户信息"""
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return user.to_dict()


# 视频路由
video_router = APIRouter(prefix="/api/videos", tags=["视频"])


@video_router.get("")
async def list_videos(
    channel: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(50, le=100),
    authorization: str = Header(None),
):
    """获取视频列表"""
    user = get_current_user(authorization)
    if not user or not user.has_permission("view_videos"):
        raise HTTPException(status_code=403, detail="Permission denied")

    service = MonitorPoolService()

    # 如果同时指定了 status 和 channel
    if status and channel:
        videos = service.get_videos_by_status_and_channel(
            VideoStatus(status), channel, limit=limit
        )
    elif channel:
        videos = service.get_videos_by_channel(channel, limit=limit)
    elif status:
        videos = service.get_videos_by_status(VideoStatus(status), limit=limit)
    else:
        # 使用流式迭代并限制数量，避免加载所有数据
        videos = []
        for video in service.iter_all_monitoring_videos(batch_size=500):
            videos.append(video)
            if len(videos) >= limit:
                break

    return {
        "total": len(videos),
        "videos": [v.to_dict() for v in videos],
    }


@video_router.get("/featured")
async def list_featured_videos(
    channel: Optional[str] = None,
    limit: int = Query(50, le=100),
    authorization: str = Header(None),
):
    """获取已上榜视频列表（用于用户界面）- 支持分层权限控制"""
    service = MonitorPoolService()
    perm_service = get_permission_service()

    # 获取当前用户（可能是游客）
    user = get_current_user(authorization)

    # 确定用户层级
    if user and user.id:
        # 已登录用户
        user_level = user.user_level
        user_id = user.id
    else:
        # 游客
        user_level = UserLevel.TOURIST
        user_id = 0

    # 获取该层级的视频条数限制
    video_limit = perm_service.get_video_list_limit(
        User(user_level=user_level) if user_level else User()
    )

    # 获取视频列表（实际limit取较小值）
    actual_limit = min(limit, video_limit)

    videos = service.get_featured_videos_by_channel(
        channel=channel or "",
        limit=actual_limit,
    )

    # 构建返回数据
    video_dicts = [v.to_dict() for v in videos]

    return {
        "total": len(videos),
        "videos": video_dicts,
        "user_level": user_level.value if user_level else "tourist",
        "video_limit": video_limit,
        "is_paid": user_level in [UserLevel.LIGHT, UserLevel.STANDARD, UserLevel.PRO] if user_level else False,
    }


@video_router.get("/cover-proxy")
def cover_proxy(url: str = Query(..., description="B站封面图片URL")):
    """
    封面图片代理接口
    解决B站图床防盗链403问题
    后端请求图片并添加正确Referer头后返回给前端
    """
    import requests
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"cover-proxy called with url: {url}")

    # 允许的B站CDN域名
    allowed_domains = ["i0.hdslb.com", "i1.hdslb.com", "i2.hdslb.com", "i3.hdslb.com"]
    is_allowed = any(url.startswith(f"https://{domain}/") for domain in allowed_domains)
    if not is_allowed:
        raise HTTPException(status_code=400, detail="Only Bilibili covers allowed")

    headers = {
        "Referer": "https://www.bilibili.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        logger.info(f"Image request status: {response.status_code}")
    except requests.RequestException as e:
        logger.error(f"Failed to fetch cover image: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch cover image")

    return Response(
        content=response.content,
        media_type=response.headers.get("Content-Type", "image/jpeg"),
        headers={
            "Cache-Control": "public, max-age=86400",
            "Access-Control-Allow-Origin": "*",
        }
    )

@video_router.get("/user-status")
async def get_user_status(
    authorization: str = Header(None),
):
    """获取当前用户状态、额度与升级信息"""
    from src.services.quota_service import get_quota_service

    user = get_current_user(authorization)
    perm_service = get_permission_service()
    quota_service = get_quota_service()

    # 确定用户层级
    if user and user.id:
        user_level = user.user_level
        user_id = user.id
    else:
        user_level = UserLevel.TOURIST
        user_id = 0

    # 获取权限信息
    perm_info = perm_service.get_user_status_info(
        User(user_level=user_level, trial_count=user.trial_count if user else 3)
    )

    # 获取额度信息
    quota_info = quota_service.get_all_quotas(user_id, user_level)

    # 游客返回试用次数
    if user_level == UserLevel.TOURIST:
        perm_info["trial_count"] = quota_service.get_trial_remaining(
            "unknown"  # 实际应从请求中获取IP
        )

    return {
        "user_level": user_level.value,
        "is_login": user is not None and user.id is not None,
        "permissions": perm_info,
        "quotas": quota_info,
    }


@video_router.post("/trial-use")
async def use_trial(
    authorization: str = Header(None),
):
    """游客扣减试用次数"""
    from src.services.quota_service import get_quota_service

    # 获取客户端IP（简化处理）
    client_ip = "unknown"

    quota_service = get_quota_service()
    remaining = quota_service.decrement_trial(client_ip)

    return {
        "success": True,
        "remaining": remaining,
        "exhausted": remaining <= 0,
    }


@video_router.get("/{bvid}")
async def get_video(bvid: str, authorization: str = Header(None)):
    """获取视频详情（公开接口，无需认证）"""
    service = MonitorPoolService()
    video = service.get_video_by_bvid(bvid)

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    # 获取视频基本信息
    result = video.to_dict()

    # 获取AI分析结果
    ai_service = get_ai_analysis_service()
    ai_analysis = ai_service.get_cached_analysis(bvid)

    if ai_analysis:
        result["ai_analysis"] = _build_analysis_response(ai_analysis)
    else:
        result["ai_analysis"] = None

    return result


@video_router.post("")
async def add_video(
    request: AddVideoRequest,
    authorization: str = Header(None),
):
    """
    手动新增视频到监控池

    1. 接收 bvid 参数
    2. 通过 B站客户端拉取视频元数据
    3. 组装 Video 实体入库
    4. 重复 BVID 返回提示而非报错
    """
    user = get_current_user(authorization)
    if not user or not user.has_permission("manage_videos"):
        raise HTTPException(status_code=403, detail="Permission denied")

    monitor_service = MonitorPoolService()

    # 检查 BVID 是否已存在
    existing = monitor_service.get_video_by_bvid(request.bvid)
    if existing:
        return AddVideoResponse(
            success=False,
            message=f"BVID {request.bvid} 已存在于监控池中",
            video=existing.to_dict(),
        )

    # 在线程池中执行同步的 B站客户端调用，避免 event loop 冲突
    def fetch_video_detail():
        updater = VideoUpdater()
        return updater.get_video_detail(request.bvid)

    detail = await asyncio.wrap_future(_executor.submit(fetch_video_detail))
    if not detail:
        raise HTTPException(status_code=404, detail=f"无法获取 BVID {request.bvid} 的视频信息，请检查 BVID 是否正确")

    # 转换 pubdate
    pubdate = None
    if detail.get("pubdate"):
        pubdate = datetime.fromtimestamp(detail["pubdate"])

    # 组装 Video 对象
    video = Video(
        bvid=detail["bvid"],
        title=detail["title"],
        author=detail["author"],
        channel=detail["channel"],
        keyword="手动入库",
        view_yesterday=0,
        view_today=detail["view_count"],
        growth_rate=0.0,
        like_count=detail["like_count"],
        favorite_count=detail["favorite_count"],
        reply_count=detail["reply_count"],
        pubdate=pubdate,
        cover_url=detail["cover_url"],
        status=VideoStatus.MONITORING,
    )

    # 入库
    try:
        saved_video = monitor_service.add_video(video)
        return AddVideoResponse(
            success=True,
            message=f"视频 {saved_video.bvid} 已成功添加到监控池",
            video=saved_video.to_dict(),
        )
    except ValueError as e:
        # 重复入库
        return AddVideoResponse(
            success=False,
            message=str(e),
            video=None,
        )


@video_router.post("/judge")
async def judge_video(
    request: HotJudgeRequest,
    authorization: str = Header(None),
):
    """判定视频是否爆款"""
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    judge_service = HotJudgeService()
    is_hot, reason = judge_service.is_hot_video(request.bvid)
    score = judge_service.get_hot_score(request.bvid)

    return HotJudgeResponse(
        is_hot=is_hot,
        reason=reason,
        score=score,
    )


# 赛道路由
channel_router = APIRouter(prefix="/api/channels", tags=["赛道"])


@channel_router.get("")
async def list_channels(authorization: str = Header(None)):
    """获取赛道列表"""
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    service = ChannelConfigService()
    channels = service.get_all_channels()

    return {
        "total": len(channels),
        "channels": [c.to_dict() for c in channels],
    }


@channel_router.get("/{channel_id}")
async def get_channel(channel_id: str, authorization: str = Header(None)):
    """获取赛道详情"""
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    service = ChannelConfigService()
    channel = service.get_channel_by_id(channel_id)

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    return channel.to_dict()


@channel_router.post("/{channel_id}/lock")
async def lock_channel(channel_id: str, authorization: str = Header(None)):
    """锁定赛道"""
    user = get_current_user(authorization)
    if not user or not user.has_permission("manage_channels"):
        raise HTTPException(status_code=403, detail="Permission denied")

    service = ChannelConfigService()
    success = service.lock_channel(channel_id)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to lock channel")

    return {"success": True}


@channel_router.post("/{channel_id}/unlock")
async def unlock_channel(channel_id: str, authorization: str = Header(None)):
    """解锁赛道"""
    user = get_current_user(authorization)
    if not user or not user.has_permission("manage_channels"):
        raise HTTPException(status_code=403, detail="Permission denied")

    service = ChannelConfigService()
    success = service.unlock_channel(channel_id)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to unlock channel")

    return {"success": True}


@channel_router.post("/calibrate")
async def calibrate_channel(
    request: CalibrateRequest,
    authorization: str = Header(None),
):
    """校准赛道参数"""
    user = get_current_user(authorization)
    if not user or not user.has_permission("manage_channels"):
        raise HTTPException(status_code=403, detail="Permission denied")

    from src.services.param_calibrator import ParamCalibrator
    calibrator = ParamCalibrator()
    success = calibrator.calibrate_channel(request.channel_id)

    if not success:
        raise HTTPException(status_code=400, detail="Calibration failed")

    return {"success": True, "calibrated_at": datetime.now().isoformat()}


# AI分析路由
ai_router = APIRouter(prefix="/api/ai", tags=["AI分析"])


@ai_router.get("/analysis/{bvid}")
async def get_video_analysis(
    bvid: str,
    authorization: str = Header(None),
):
    """获取视频AI分析结果（仅返回已保存的分析，不触发新分析）"""
    user = get_current_user(authorization)
    if not user or not user.has_permission("view_ai_analysis"):
        raise HTTPException(status_code=403, detail="VIP privilege required")

    ai_service = get_ai_analysis_service()

    # 仅从缓存获取，不触发新分析
    cached = ai_service.get_cached_analysis(bvid)
    if cached:
        return {
            "cached": True,
            "analysis": _build_analysis_response(cached),
        }

    # 无缓存时返回null
    return {
        "cached": False,
        "analysis": None,
    }


def _build_analysis_response(analysis: "AIAnalysisResult") -> dict:
    """构建AI分析响应数据"""
    response = {
        "bvid": analysis.bvid,
        "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
    }

    # 封面分析（7个维度）
    if analysis.cover_analysis:
        cover = analysis.cover_analysis
        response["cover_analysis"] = {
            "cover_composition": cover.cover_composition,
            "cover_main_element": cover.cover_main_element,
            "cover_color_scheme": cover.cover_color_scheme,
            "cover_visual_style": cover.cover_visual_style,
            "cover_mood_atmosphere": cover.cover_mood_atmosphere,
            "cover_visual_highlights": cover.cover_visual_highlights or [],
            "cover_audience_expectation": cover.cover_audience_expectation,
        }
    else:
        response["cover_analysis"] = None

    # 内容分析（4个维度）
    if analysis.content_analysis:
        content = analysis.content_analysis
        response["content_analysis"] = {
            "topic_summary": content.topic_summary,
            "viral_logic_analysis": content.viral_logic_analysis,
            "content_optimization_suggestions": content.content_optimization_suggestions,
            "replicability_evaluation": content.replicability_evaluation,
        }
    else:
        response["content_analysis"] = None

    return response


# 用户管理路由 (管理员专用)
user_router = APIRouter(prefix="/api/users", tags=["用户管理"])


@user_router.get("")
async def list_users(authorization: str = Header(None)):
    """获取用户列表"""
    user = get_current_user(authorization)
    if not user or not user.has_permission("manage_users"):
        raise HTTPException(status_code=403, detail="Admin privilege required")

    auth_service = get_auth_service()
    users = auth_service.get_all_users()

    return {
        "total": len(users),
        "users": [u.to_dict() for u in users],
    }


@user_router.post("/{user_id}/role")
async def update_user_role(
    user_id: int,
    role: str = Body(..., embed=True),
    authorization: str = Header(None),
):
    """更新用户角色"""
    user = get_current_user(authorization)
    if not user or not user.has_permission("manage_users"):
        raise HTTPException(status_code=403, detail="Admin privilege required")

    try:
        new_role = UserRole(role)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role")

    auth_service = get_auth_service()
    success = auth_service.update_user_role(user_id, new_role)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to update role")

    return {"success": True}


# ============== Dashboard Data API ==============

dashboard_router = APIRouter(prefix="/api/dashboard", tags=["仪表盘"])


@dashboard_router.get("/stats")
async def get_dashboard_stats(authorization: str = Header(None)):
    """获取仪表盘统计数据"""
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    monitor_service = MonitorPoolService()
    channel_service = ChannelConfigService()

    # 获取各状态视频数量
    monitoring_count = len(monitor_service.get_videos_by_status(VideoStatus.MONITORING, limit=10000))
    featured_count = len(monitor_service.get_videos_by_status(VideoStatus.FEATURED, limit=10000))
    declined_count = len(monitor_service.get_videos_by_status(VideoStatus.DECLINED, limit=10000))

    # 获取赛道数量
    channels = channel_service.get_all_channels()
    channel_count = len(channels)
    locked_count = sum(1 for c in channels if c.is_locked)

    return {
        "videos": {
            "monitoring": monitoring_count,
            "featured": featured_count,
            "declined": declined_count,
            "total": monitoring_count + featured_count + declined_count,
        },
        "channels": {
            "total": channel_count,
            "locked": locked_count,
            "unlocked": channel_count - locked_count,
        },
        "timestamp": datetime.now().isoformat(),
    }


@dashboard_router.get("/featured")
async def get_featured_videos(
    limit: int = Query(10, le=50),
    authorization: str = Header(None),
):
    """获取爆款视频列表"""
    user = get_current_user(authorization)
    if not user or not user.has_permission("view_videos"):
        raise HTTPException(status_code=403, detail="Permission denied")

    judge_service = HotJudgeService()
    videos = judge_service.get_featured_videos(limit=limit)

    return {
        "total": len(videos),
        "videos": [v.to_dict() for v in videos],
    }


# ============== 订阅管理API ==============

class SubscribeRequest(BaseModel):
    tier: str  # light / standard / pro
    payment_method: str = "wechat"


class PaymentCallbackRequest(BaseModel):
    order_id: int
    transaction_id: str
    status: str  # success / failed


subscribe_router = APIRouter(prefix="/api/subscribe", tags=["订阅"])


@subscribe_router.get("/tiers")
async def get_subscription_tiers():
    """获取所有订阅套餐"""
    service = get_subscription_service()
    return {
        "tiers": service.get_subscription_tiers(),
    }


@subscribe_router.post("/create")
async def create_subscription(
    request: SubscribeRequest,
    authorization: str = Header(None),
):
    """创建订阅订单"""
    user = get_current_user(authorization)
    if not user or not user.id:
        raise HTTPException(status_code=401, detail="请先登录")

    from src.models.subscription import SubscribeTier
    try:
        tier = SubscribeTier(request.tier)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的套餐类型")

    service = get_subscription_service()
    order = service.create_subscription(
        user_id=user.id,
        tier=tier,
        payment_method=request.payment_method,
    )

    if not order:
        raise HTTPException(status_code=500, detail="创建订单失败")

    return {
        "success": True,
        "order": order.to_dict(),
        "payment_url": f"/api/subscribe/pay/{order.id}",  # 模拟支付链接
    }


@subscribe_router.post("/pay/{order_id}")
async def pay_subscription(
    order_id: int,
    authorization: str = Header(None),
):
    """
    模拟支付订阅订单
    实际项目中应调用微信/支付宝等支付平台
    """
    service = get_subscription_service()

    # 模拟支付成功
    transaction_id = f"mock_txn_{order_id}_{datetime.now().timestamp()}"
    success = service.process_payment(order_id, transaction_id)

    if not success:
        raise HTTPException(status_code=400, detail="支付失败")

    return {
        "success": True,
        "message": "支付成功",
        "transaction_id": transaction_id,
    }


@subscribe_router.post("/payment-callback")
async def payment_callback(request: PaymentCallbackRequest):
    """
    支付平台回调接口（模拟）
    实际项目中应由支付平台调用
    """
    service = get_subscription_service()

    if request.status == "success":
        success = service.process_payment(request.order_id, request.transaction_id)
        return {"success": success}
    else:
        return {"success": False, "message": "支付失败"}


@subscribe_router.get("/my")
async def get_my_subscription(
    authorization: str = Header(None),
):
    """获取当前用户订阅信息"""
    user = get_current_user(authorization)
    if not user or not user.id:
        raise HTTPException(status_code=401, detail="请先登录")

    service = get_subscription_service()
    subscription = service.get_user_subscription(user.id)

    return {
        "subscription": subscription,
        "tiers": service.get_subscription_tiers() if not subscription else None,
    }


@subscribe_router.post("/cancel")
async def cancel_subscription(
    authorization: str = Header(None),
):
    """取消订阅（不退款，到期后降级）"""
    user = get_current_user(authorization)
    if not user or not user.id:
        raise HTTPException(status_code=401, detail="请先登录")

    service = get_subscription_service()
    success = service.cancel_subscription(user.id)

    if not success:
        raise HTTPException(status_code=500, detail="取消订阅失败")

    return {"success": True, "message": "已取消订阅，到期后将降级为免费用户"}


@subscribe_router.post("/auto-renew")
async def set_auto_renew(
    enable: bool = Body(..., embed=True),
    authorization: str = Header(None),
):
    """设置自动续费"""
    user = get_current_user(authorization)
    if not user or not user.id:
        raise HTTPException(status_code=401, detail="请先登录")

    service = get_subscription_service()

    if enable:
        service.enable_auto_renew(user.id)
    else:
        service.disable_auto_renew(user.id)

    return {"success": True, "auto_renew": enable}


# ============== 成本统计API ==============

from src.services.cost_statistics_service import get_cost_statistics_service

cost_router = APIRouter(prefix="/api/cost", tags=["成本统计"])


@cost_router.get("/summary")
async def get_cost_summary(
    authorization: str = Header(None),
):
    """获取成本汇总（管理员专用）"""
    user = get_current_user(authorization)
    if not user or not user.has_permission("manage_users"):
        raise HTTPException(status_code=403, detail="Admin privilege required")

    service = get_cost_statistics_service()
    summary = service.get_cost_summary()

    return summary


@cost_router.get("/daily")
async def get_daily_cost(
    date: Optional[str] = Query(None, description="日期 YYYY-MM-DD"),
    authorization: str = Header(None),
):
    """获取每日成本统计"""
    user = get_current_user(authorization)
    if not user or not user.has_permission("manage_users"):
        raise HTTPException(status_code=403, detail="Admin privilege required")

    service = get_cost_statistics_service()

    target_date = datetime.now()
    if date:
        target_date = datetime.fromisoformat(date)

    daily_cost = service.get_daily_cost(target_date)

    return daily_cost


@cost_router.get("/monthly")
async def get_monthly_cost(
    year: Optional[int] = Query(None, description="年份"),
    month: Optional[int] = Query(None, description="月份"),
    authorization: str = Header(None),
):
    """获取月度成本统计"""
    user = get_current_user(authorization)
    if not user or not user.has_permission("manage_users"):
        raise HTTPException(status_code=403, detail="Admin privilege required")

    service = get_cost_statistics_service()
    monthly_cost = service.get_monthly_cost(year, month)

    return monthly_cost


@cost_router.get("/user/{user_id}")
async def get_user_cost(
    user_id: int,
    days: int = Query(30, description="统计天数"),
    authorization: str = Header(None),
):
    """获取指定用户的成本统计"""
    user = get_current_user(authorization)
    if not user or not user.has_permission("manage_users"):
        raise HTTPException(status_code=403, detail="Admin privilege required")

    service = get_cost_statistics_service()
    user_cost = service.get_user_cost(user_id, days)

    return user_cost


@cost_router.get("/my")
async def get_my_cost(
    days: int = Query(30, description="统计天数"),
    authorization: str = Header(None),
):
    """获取当前用户的成本统计"""
    user = get_current_user(authorization)
    if not user or not user.id:
        raise HTTPException(status_code=401, detail="请先登录")

    service = get_cost_statistics_service()
    user_cost = service.get_user_cost(user.id, days)

    return user_cost