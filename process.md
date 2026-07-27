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
