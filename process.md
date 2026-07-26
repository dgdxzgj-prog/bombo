# BOMBO 项目进度记录

## 更新日期: 2026-07-24

---

## 1. AI 分析功能扩展

### 完成内容
- **扩展 AI 内容分析的输入端**：将可用的视频数据字段全部传入 AI 分析提示词

### 新增输入字段
| 字段 | 说明 |
|------|------|
| duration | 视频时长（格式化显示，如"5分钟30秒"） |
| tags | 视频标签（最多10个） |
| view_today | 当日播放量 |
| growth_rate | 24小时增速百分比 |
| like_count | 点赞数 |
| favorite_count | 收藏数 |
| reply_count | 评论数 |
| coin_count | 投币数 |
| share_count | 分享数 |
| author_fans | 粉丝数 |

### 修改文件
- `src/skills/ai_analysis_skills.py` - 更新 CONTENT_ANALYSIS_SKILL 模板
- `src/services/ai_analysis_service.py` - 更新 `_build_content_prompt` 方法

---

## 2. 移动端 UI 优化

### 完成内容

#### 2.1 视频详情页右滑返回
- 支持从屏幕左侧边缘右滑超过 100px 返回榜单
- 首次进入显示滑动提示 toast（3秒后消失）
- 通过 sessionStorage 记录是否已显示过提示

#### 2.2 榜单页面位置保持
- 滚动时自动保存滚动位置到 sessionStorage
- 同时保存当前筛选的频道状态
- 返回榜单时自动恢复到之前的滚动位置和频道筛选

#### 2.3 榜单页视频卡片改造
- 将"AI分析"按钮改为显示粉丝量和发布时间
- 格式：
  - 粉丝量：`XX万粉丝` 或具体数字
  - 发布时间：`X月X日`
- 保留跳转B站按钮

#### 2.4 视频封面添加时长显示
- 在封面右下角显示视频时长
- 样式：半透明黑色背景白色文字
- 格式：`MM:SS`（超过1小时显示 `HH:MM:SS`）

### 修改文件
- `frontend/src/app/m/page.tsx` - 榜单页面改造
- `frontend/src/app/m/video/[bvid]/page.tsx` - 视频详情页右滑返回
- `frontend/src/app/globals.css` - 添加 fade-in-out 动画

---

## 3. 数据库迁移

### 完成内容
- 为 `monitor_pool` 表添加 `duration` 和 `tags` 字段
- 为 `video_history` 表添加 `duration` 和 `tags` 字段

### SQL 脚本
- `scripts/migration_duration_tags.sql`

### 字段说明
| 字段 | 类型 | 说明 |
|------|------|------|
| duration | INTEGER | 视频时长（秒） |
| tags | JSONB | 视频标签列表 |

---

## 4. 服务层修复

### 完成内容
- 修复 `monitor_pool_service.py` 中 `_row_to_video_with_channel_from_vc` 方法的列索引映射
- SQL 查询添加 `duration` 和 `tags` 列
- 修正列索引对应关系

### 修改文件
- `src/services/monitor_pool_service.py`

---

## 5. 模型修复

### 完成内容
- 修复 `Video` 模型缺少 `List` 导入问题

### 修改文件
- `src/models/video.py`

---

## 6. 定时任务

### 任务状态

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

### 已暂停任务
- `Author Collection` (UP主信息采集任务) - 已注释暂停

### 暂停原因
- B站 API 返回 -799 错误，账号视频状态异常
- 需要更换 cookie 或等待账号恢复

---

## 7. 历史进度记录

### 视频状态分离与赛道自适应爆款判定 (2026-07-24 之前)

详见上方文档历史记录部分。

---

## 待办事项

1. [ ] 重新启用 Author Collection 任务（需更换有效 cookie）
2. [ ] 执行数据库迁移后验证 duration 和 tags 字段是否正常采集
3. [ ] 验证 AI 分析新输入是否生效
