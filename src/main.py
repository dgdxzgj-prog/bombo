"""
BOMBO Web Application
FastAPI主应用
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
import os
import threading

from src.api.api_router import (
    auth_router,
    video_router,
    channel_router,
    ai_router,
    user_router,
    dashboard_router,
    subscribe_router,
    cost_router,
)
from src.tasks.video_tasks import init_video_tasks
from src.tasks.subscription_tasks import init_subscription_tasks
from src.tasks.scheduler import get_scheduler


# 创建FastAPI应用
app = FastAPI(
    title="BOMBO - B站视频热度监控系统",
    description="自适应多信号综合判定系统，智能识别爆款视频",
    version="1.0.0",
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 获取当前目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# 配置模板
if os.path.exists(TEMPLATES_DIR):
    templates = Jinja2Templates(directory=TEMPLATES_DIR)

# 挂载静态文件
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ============== 注册路由 ==============

app.include_router(auth_router)
app.include_router(video_router)
app.include_router(channel_router)
app.include_router(ai_router)
app.include_router(user_router)
app.include_router(dashboard_router)
app.include_router(subscribe_router)
app.include_router(cost_router)


# ============== 启动定时任务调度器 ==============

def start_scheduler():
    """在新线程中启动调度器"""
    scheduler = get_scheduler()
    init_video_tasks()  # 初始化视频任务
    init_subscription_tasks()  # 初始化订阅与额度任务
    scheduler.start()
    print("[Scheduler] All task schedulers started")

# 启动调度器线程
scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
scheduler_thread.start()


# ============== 根路由 ==============

@app.get("/", response_class=HTMLResponse)
async def root():
    """首页"""
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>BOMBO - B站视频热度监控系统</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .container {
                text-align: center;
                color: white;
            }
            h1 {
                font-size: 4rem;
                margin-bottom: 1rem;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }
            .subtitle {
                font-size: 1.5rem;
                opacity: 0.9;
                margin-bottom: 2rem;
            }
            .features {
                display: flex;
                gap: 2rem;
                justify-content: center;
                flex-wrap: wrap;
                margin-top: 3rem;
            }
            .feature {
                background: rgba(255,255,255,0.1);
                padding: 1.5rem 2rem;
                border-radius: 12px;
                backdrop-filter: blur(10px);
            }
            .feature h3 { font-size: 1.2rem; margin-bottom: 0.5rem; }
            .feature p { opacity: 0.8; font-size: 0.9rem; }
            .btn {
                display: inline-block;
                margin-top: 2rem;
                padding: 1rem 2rem;
                background: white;
                color: #667eea;
                text-decoration: none;
                border-radius: 50px;
                font-weight: bold;
                transition: transform 0.2s;
            }
            .btn:hover { transform: scale(1.05); }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>BOMBO</h1>
            <p class="subtitle">B站视频热度监控系统 - 自适应多信号综合判定</p>

            <div class="features">
                <div class="feature">
                    <h3>三层筛选</h3>
                    <p>爆发层 / 兜底层 / 冷启动</p>
                </div>
                <div class="feature">
                    <h3>AI双模型</h3>
                    <p>Gemini + DeepSeek</p>
                </div>
                <div class="feature">
                    <h3>自动校准</h3>
                    <p>参数自适应调整</p>
                </div>
            </div>

            <a href="/dashboard" class="btn">进入控制台</a>
        </div>
    </body>
    </html>
    """
    return html_content


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """仪表盘页面"""
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>控制台 - BOMBO</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100">
        <!-- 导航栏 -->
        <nav class="bg-indigo-600 text-white p-4">
            <div class="container mx-auto flex justify-between items-center">
                <h1 class="text-xl font-bold">BOMBO 控制台</h1>
                <div id="user-info" class="text-sm"></div>
            </div>
        </nav>

        <div class="container mx-auto p-6">
            <!-- 统计卡片 -->
            <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
                <div class="bg-white rounded-lg shadow p-6">
                    <h3 class="text-gray-500 text-sm">监控中</h3>
                    <p id="stat-monitoring" class="text-3xl font-bold text-blue-600">-</p>
                </div>
                <div class="bg-white rounded-lg shadow p-6">
                    <h3 class="text-gray-500 text-sm">已上榜</h3>
                    <p id="stat-featured" class="text-3xl font-bold text-green-600">-</p>
                </div>
                <div class="bg-white rounded-lg shadow p-6">
                    <h3 class="text-gray-500 text-sm">已衰退</h3>
                    <p id="stat-declined" class="text-3xl font-bold text-gray-600">-</p>
                </div>
                <div class="bg-white rounded-lg shadow p-6">
                    <h3 class="text-gray-500 text-sm">赛道数</h3>
                    <p id="stat-channels" class="text-3xl font-bold text-purple-600">-</p>
                </div>
            </div>

            <!-- 监控池视频列表 -->
            <div class="bg-white rounded-lg shadow p-6 mb-6">
                <h2 class="text-lg font-bold mb-4">监控池视频</h2>
                <div id="pool-list" class="space-y-3">
                    <p class="text-gray-500">加载中...</p>
                </div>
            </div>

            <!-- 登录表单 (未登录时显示) -->
            <div id="login-form" class="bg-white rounded-lg shadow p-6 max-w-md mx-auto">
                <h2 class="text-lg font-bold mb-4">登录</h2>
                <input type="text" id="username" placeholder="用户名" class="w-full p-2 border rounded mb-3">
                <input type="password" id="password" placeholder="密码" class="w-full p-2 border rounded mb-3">
                <button onclick="login()" class="w-full bg-indigo-600 text-white p-2 rounded">登录</button>
                <p id="login-error" class="text-red-500 text-sm mt-2 hidden"></p>
            </div>
        </div>

        <script>
            const API_BASE = '/api';

            // 加载统计数据
            async function loadStats() {
                try {
                    const res = await fetch(`${API_BASE}/dashboard/stats`);
                    if (!res.ok) return;
                    const data = await res.json();
                    document.getElementById('stat-monitoring').textContent = data.videos.monitoring;
                    document.getElementById('stat-featured').textContent = data.videos.featured;
                    document.getElementById('stat-declined').textContent = data.videos.declined;
                    document.getElementById('stat-channels').textContent = data.channels.total;
                } catch (e) {
                    console.error('Failed to load stats:', e);
                }
            }

            // 获取状态标签
            function getStatusBadge(status) {
                const badges = {
                    'monitoring': '<span class="px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-600">监控中</span>',
                    'featured': '<span class="px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-600">已上榜</span>',
                    'declined': '<span class="px-2 py-1 rounded text-xs font-medium bg-gray-100 text-gray-600">已衰退</span>'
                };
                return badges[status] || status;
            }

            // 加载监控池视频
            async function loadPoolVideos() {
                try {
                    const res = await fetch(`${API_BASE}/videos?limit=100`, {
                        headers: {'Authorization': 'Bearer ' + (localStorage.getItem('token') || '')}
                    });
                    if (!res.ok) return;
                    const data = await res.json();
                    const list = document.getElementById('pool-list');
                    if (data.videos.length === 0) {
                        list.innerHTML = '<p class="text-gray-500">暂无视频数据</p>';
                        return;
                    }
                    list.innerHTML = data.videos.map(v => `
                        <div class="flex items-center justify-between p-3 bg-gray-50 rounded">
                            <div class="flex items-center gap-3">
                                ${getStatusBadge(v.status)}
                                <div>
                                    <a href="/video/${v.bvid}" class="font-medium text-blue-600 hover:underline">${v.title}</a>
                                    <p class="text-sm text-gray-500">${v.author} | ${v.channel}</p>
                                </div>
                            </div>
                            <div class="text-right">
                                <p class="font-bold ${v.growth_rate >= 0 ? 'text-green-600' : 'text-red-600'}">${v.growth_rate >= 0 ? '+' : ''}${v.growth_rate}%</p>
                                <p class="text-sm text-gray-500">${v.view_today?.toLocaleString() || 0} 播放</p>
                            </div>
                        </div>
                    `).join('');
                } catch (e) {
                    console.error('Failed to load pool videos:', e);
                    document.getElementById('pool-list').innerHTML = '<p class="text-red-500">加载失败</p>';
                }
            }

            // 登录
            async function login() {
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                const errorEl = document.getElementById('login-error');

                try {
                    const res = await fetch(`${API_BASE}/auth/login`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({username, password})
                    });

                    if (!res.ok) {
                        errorEl.textContent = '登录失败';
                        errorEl.classList.remove('hidden');
                        return;
                    }

                    const data = await res.json();
                    localStorage.setItem('token', data.token);
                    localStorage.setItem('user', JSON.stringify(data.user));

                    document.getElementById('login-form').classList.add('hidden');
                    document.getElementById('user-info').textContent = `欢迎, ${data.user.username}`;
                    loadStats();
                    loadPoolVideos();
                } catch (e) {
                    errorEl.textContent = '登录失败: ' + e.message;
                    errorEl.classList.remove('hidden');
                }
            }

            // 初始化
            const token = localStorage.getItem('token');
            if (token) {
                document.getElementById('login-form').classList.add('hidden');
                const user = JSON.parse(localStorage.getItem('user') || '{}');
                document.getElementById('user-info').textContent = `欢迎, ${user.username}`;
                loadStats();
                loadPoolVideos();
            } else {
                loadStats();
            }
        </script>
    </body>
    </html>
    """
    return html_content


@app.get("/video/{bvid}", response_class=HTMLResponse)
async def video_detail(bvid: str):
    """视频详情页"""
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>视频详情 - BOMBO</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100">
        <nav class="bg-indigo-600 text-white p-4">
            <div class="container mx-auto">
                <a href="/dashboard" class="text-white hover:underline">← 返回控制台</a>
            </div>
        </nav>

        <div class="container mx-auto p-6">
            <div class="bg-white rounded-lg shadow p-6">
                <h2 class="text-2xl font-bold mb-4">视频详情: {bvid}</h2>
                <div id="video-info">
                    <p class="text-gray-500">加载中...</p>
                </div>
            </div>
        </div>

        <script>
            async function loadVideo() {{
                try {{
                    const res = await fetch(`/api/videos/{bvid}`);
                    if (!res.ok) throw new Error('Video not found');
                    const video = await res.json();
                    document.getElementById('video-info').innerHTML = `
                        <div class="grid grid-cols-2 gap-4">
                            <div><strong>标题:</strong> ${{video.title}}</div>
                            <div><strong>作者:</strong> ${{video.author}}</div>
                            <div><strong>赛道:</strong> ${{video.channel}}</div>
                            <div><strong>状态:</strong> ${{video.status}}</div>
                            <div><strong>今日播放:</strong> ${{video.view_today}}</div>
                            <div><strong>昨日播放:</strong> ${{video.view_yesterday}}</div>
                            <div><strong>增速:</strong> ${{video.growth_rate}}%</div>
                            <div><strong>点赞:</strong> ${{video.like_count}}</div>
                        </div>
                    `;
                }} catch (e) {{
                    document.getElementById('video-info').innerHTML = '<p class="text-red-500">视频不存在</p>';
                }}
            }}
            loadVideo();
        </script>
    </body>
    </html>
    """
    return html_content


# ============== 健康检查 ==============

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "bombo"}


@app.get("/debug/scheduler")
async def debug_scheduler():
    """调度器调试端点"""
    from src.tasks.scheduler import get_scheduler
    scheduler = get_scheduler()
    return {
        "running": scheduler._running,
        "tasks": [
            {
                "id": t.task_id,
                "name": t.name,
                "enabled": t.enabled,
                "interval": t.interval_seconds,
                "last_run": t.last_run.isoformat() if t.last_run else None,
            }
            for t in scheduler.tasks.values()
        ]
    }


# ============== 错误处理 ==============

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc) if hasattr(exc, '__str__') else "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
