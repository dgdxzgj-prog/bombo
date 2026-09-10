# BOMBO 项目进度记录

## 更新日期: 2026-07-27

---

## 1. 本地开发环境

### 完成内容
- ✅ 端口 8000 (FastAPI 后端) 和 3000 (Next.js 前端) 已启动并验证
- ✅ Dashboard 页面"赛道数量"改为"AI分析视频数量"
- ✅ 前端 npm build 完成，构建成功无错误
- ✅ 删除包含敏感 API Key 的测试文件 (test_ai.bat, test_ai_task.py)
- ✅ 添加 numpy 依赖到 requirements.txt (修复 track_adaptive_threshold_service.py 报错)

### 修改文件
- `src/api/api_router.py` - 添加 get_db_session 和 text 导入，ai_analyzed 字段
- `frontend/src/types/index.ts` - DashboardStats 添加 ai_analyzed 字段
- `frontend/src/app/(dashboard)/dashboard/page.tsx` - UI 改为"AI分析视频"
- `requirements.txt` - 添加 numpy==1.26.3

---

## 2. 数据库迁移

### 完成内容
- ✅ 导出用户表：`D:\work\bombo\bombo\user_backup.sql` (4.2 KB)
- ⚠️ 导出完整数据库遇到 track_online_history 表权限问题，已排除

### 服务器数据库状态
```
NAME             STATUS
bombo-backend    Running (Restarting 循环，可能 numpy 缺失)
bombo-frontend   Up 2 minutes
bombo-nginx      Up 2 minutes (端口 80/443)
bombo-postgres   Up 2 minutes (healthy, 端口 5432)
bombo-redis      Up 2 minutes (healthy, 端口 6379)
```

### 待迁移
- [x] 用户表已导出
- [ ] 完整数据库迁移（需先解决 track_online_history 权限问题）

---

## 3. 服务器部署问题

### 问题：登录 Network Error

**根本原因：**
Frontend Dockerfile 中 `NEXT_PUBLIC_API_URL=http://localhost:8000` 硬编码，导致生产环境前端请求 localhost:8000 而非实际后端地址。

**涉及文件：**
- `/opt/bombo/frontend/Dockerfile`: `ENV NEXT_PUBLIC_API_URL=http://localhost:8000`
- `/opt/bombo/frontend/src/lib/api.ts`: `const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";`

**验证结果：**
- ✅ nginx → backend: `curl http://backend:8000/health` 正常
- ✅ 后端直连: `curl http://localhost:8000/health` 正常
- ❌ 外部访问: `curl https://meng-yuan.uk/api/health` 返回 404

**解决方案：**
修改 docker-compose.yml 中的 frontend 配置，添加构建参数：
```yaml
frontend:
  build:
    context: ./frontend
    args:
      - NEXT_PUBLIC_API_URL=https://meng-yuan.uk
```

然后重建：
```bash
docker compose build frontend
docker compose up -d frontend
```

---

## 4. 定时任务状态

| 任务ID | 名称 | 执行频率 | 状态 |
|--------|------|----------|------|
| region_ranking | Region Ranking | 每6小时 | 运行中 |
| daily_hot | Daily Hot Videos | 每小时 | 运行中 |
| hourly_video_update | Hourly Video Update | 每小时:05 | 运行中 |
| ai_analyze_featured | AI Analyze Featured Videos | 每小时:15 | 运行中 |
| author_collection | Author Collection | 每小时:25 | **已暂停** |
| daily_track_threshold | Daily Track Threshold | 每天01:00 | 运行中 |
| daily_video_judgment | Daily Video Judgment | 每天06:00 | 运行中 |
| video_cleanup | Video Cleanup | 每天06:30 | 运行中 |
| daily_quota_reset | Daily Quota Reset | 每天0点 | 运行中 |
| monthly_quota_reset | Monthly Quota Reset | 每月1号0点 | 运行中 |
| subscription_expiry_check | Subscription Expiry Check | 每小时 | 运行中 |
| subscription_renewal_reminder | Subscription Renewal Reminder | 每天8点 | 运行中 |
| auto_renew | Auto Renew | 每天1点 | 运行中 |

---

## 5. 待办事项

1. [ ] 修复 frontend NEXT_PUBLIC_API_URL 配置
2. [ ] 重新构建并部署 frontend
3. [ ] 验证登录功能
4. [ ] 检查 backend 是否因 numpy 问题需要重建
5. [ ] 重新启用 Author Collection 任务（需更换有效 cookie）
6. [ ] 完整迁移数据库（解决 track_online_history 权限问题）

---

## 6. 相关路径

| 类型 | 路径 |
|------|------|
| 本地项目 | `D:\work\bombo\bombo\` |
| 服务器项目 | `/opt/bombo/` |
| 用户表备份 | `D:\work\bombo\bombo\user_backup.sql` |
| 数据库备份 | `D:\work\bombo\bombo\bombo_backup.sql` (不完整) |

---

## 更新日期: 2026-09-09

---

### 1. B站风控问题处理

#### 问题描述
服务器 IP 被 B站 风控，`hourly_video_update` 任务出现大量 412 错误：
```
Get video detail error: 网络错误，状态码：412 - <!DOCTYPE html>
```

#### 解决方案

##### 1.1 反爬策略增强

**文件**: `src/services/snapshot_service.py`

| 优化项 | 修改内容 |
|--------|----------|
| 随机延时 | 从 1-3秒 增加到 2-5秒 |
| 412重试机制 | 新增 `_get_video_detail_with_retry` 方法，指数退避重试（最多3次） |

**重试策略**:
| 重试次数 | 基础延时 | 最大延时 |
|---------|---------|---------|
| 第1次 | 4s | 6s |
| 第2次 | 8s | 10s |
| 第3次 | 16s | 18s |

##### 1.2 禁用服务端 hourly_video_update 任务

由于服务器 IP 已被风控，暂时禁用 `hourly_video_update` 任务：

**文件**: `src/tasks/video_tasks.py`

```python
# [已暂停] - 2026-09-09 - 服务器IP被B站风控
# scheduler.add_interval_task(
#     task_id="hourly_video_update",
#     name="Hourly Video Update",
#     func=hourly_video_update_task,
#     interval_seconds=3600,
# )
```

同时注释掉对应的 `_schedule_task` 调用：
```python
# [已暂停] hourly_video_update - 2026-09-09 服务器IP被B站风控
# scheduler._schedule_task(scheduler.tasks["hourly_video_update"], initial_delay=300)
```

---

### 2. 本地独立任务程序

#### 2.1 创建目的
由于服务器 IP 被 B站 风控，创建本地任务程序在本地环境运行以下任务：
- `hourly_video_update` - 快照采集
- `hourly_user_feed_update` - 用户订阅更新
- `daily_keyword_refresh` - 每日关键词刷新
- `daily_featured_settlement` - 每日上榜结算

#### 2.2 文件位置
```
scripts/local_crawler_runner.py
```

#### 2.3 使用方法

```bash
# 运行所有任务
python scripts/local_crawler_runner.py

# 只运行小时级任务
python scripts/local_crawler_runner.py hourly

# 只运行日级任务
python scripts/local_crawler_runner.py daily
```

#### 2.4 反爬策略
`hourly_user_feed_update` 采用与 `hourly_video_update` 相同的反爬策略：
- 请求前随机延时 2-5 秒
- 412 错误指数退避重试（最多3次）

#### 2.5 云数据库配置
已配置连接 Supabase 云数据库：
```python
os.environ["DATABASE_URL"] = "postgresql+psycopg2://postgres.ryklhtuzrsdgcjbkqqyn:***@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres?sslmode=require"
```

**连接测试结果**:
| 项目 | 结果 |
|------|------|
| 连接状态 | ✅ 成功 |
| PostgreSQL 版本 | 17.6 |
| monitor_pool 记录数 | 1301 |
| user_monitor_pool 记录数 | 5 |

---

### 3. 当前定时任务状态

#### 服务端运行中的任务

| 任务ID | 名称 | 执行时间 | 状态 |
|--------|------|----------|------|
| region_ranking | Region Ranking | 每6小时 | 运行中 |
| daily_hot | Daily Hot Videos | 每小时 | 运行中 |
| ai_analyze_featured | AI Analyze Featured Videos | 每小时:10 | 运行中 |
| daily_track_threshold | Daily Track Threshold | 每天01:00 | 运行中 |
| daily_video_judgment | Daily Video Judgment | 每天06:00 | 运行中 |
| video_cleanup | Video Cleanup | 每天06:30 | 运行中 |
| daily_quota_reset | Daily Quota Reset | 每天00:00 | 运行中 |
| monthly_quota_reset | Monthly Quota Reset | 每月1号00:00 | 运行中 |
| subscription_expiry_check | Subscription Expiry Check | 每小时 | 运行中 |
| subscription_renewal_reminder | Subscription Renewal Reminder | 每天08:00 | 运行中 |
| auto_renew | Auto Renew | 每天01:00 | 运行中 |

#### 服务端已暂停的任务

| 任务ID | 名称 | 原因 |
|--------|------|------|
| video_discovery | Video Discovery | 已注释停用 |
| author_collection | Author Collection | 已注释停用 |
| hourly_video_update | Hourly Video Update | **2026-09-09 服务器IP被B站风控** |

#### 本地独立任务程序

| 任务 | 说明 | 反爬策略 |
|------|------|----------|
| hourly_video_update | 快照采集 | 2-5秒延时 + 412重试 |
| hourly_user_feed_update | 用户订阅更新 | 2-5秒延时 + 412重试 |
| daily_keyword_refresh | 每日关键词刷新 | 原有策略 |
| daily_featured_settlement | 每日上榜结算 | 无需爬虫 |

---

### 4. 待办事项

1. [ ] 本地运行 `hourly_video_update` 任务，补充服务器端暂停的数据采集
2. [ ] 观察云数据库 monitor_pool 增长情况
3. [ ] 考虑更换服务器 IP 或使用代理池解除 B站 风控
4. [ ] 后续可重新启用 hourly_video_update 任务

---
