# BOMBO 视频页面改造进度

## 更新日期
2026-07-19 01:05

## 需求概述
1. 视频列表页面B站风格改造（卡片网格展示）
2. 爆款判定系统修复（支持fallback逻辑和默认赛道配置）
3. 增速数据持久化修复
4. 逆向降级逻辑（P0规范）
5. 封面图片显示问题排查修复

---

## 一、前端页面改造

### 已完成功能

#### 1. 布局排版
- 4列卡片网格布局（一行固定4个视频卡片）
- 参考B站搜索结果样式

#### 2. 视频卡片展示字段
从左到右、从上到下：
- **封面图片**：16:9比例，使用`<img>`标签直接加载
- **右上角色标**：
  - 成熟视频（入库≥24h）：显示增速百分比
    - 红色边框（border-red-500）：增速≥5%
    - 橙色边框（border-orange-500）：增速≥1%
    - 灰色边框（border-gray-500）：增速<1%
  - 冷启动视频（入库<24h）：显示紫色边框的"预测"标签（border-purple-400）
- **标题**：最多2行，超出省略
- **作者**：单行显示
- **播放量和点赞数**：底部并排显示

#### 3. 排序规则
- 默认按增速降序排列

#### 4. 赛道筛选
- 支持按赛道筛选（动画，音乐，游戏等22个赛道）

#### 5. 搜索功能
- 支持按视频标题或作者名称搜索

### 技术实现
- 文件：`frontend/src/app/(dashboard)/videos/page.tsx`
- 使用原生`fetch`直接调用API（避免React Query重复定义问题）
- 使用`<img>`标签替代Next.js的`Image`组件
- API接口：`GET /api/videos/featured?channel=&limit=100`
- **已添加** `crossOrigin="anonymous"` 属性解决跨域问题

### 配置文件修改
- 文件：`frontend/next.config.mjs`
- 添加hdslb.com图片域名配置（remotePatterns）

### API修复
- 文件：`frontend/src/lib/api.ts`
- 修复`getFeaturedVideos`重复定义问题
- 使用`/api/videos/featured`接口（无需认证）

---

## 二、后端爆款判定系统修复

### 问题1：滑动窗口数据不足
- **现象**：系统运行不足24小时，快照数据不完整
- **原因**：滑动窗口需要24小时数据才能计算真实增速
- **修复**：添加fallback逻辑，当滑动窗口数据不足时使用视频原有的`growth_rate`字段

### 问题2：赛道配置缺失
- **现象**：很多视频的赛道（如"时尚"、"电影"、"资讯"等）没有对应配置
- **原因**：数据库中有20+个赛道，但配置表只有8个
- **修复**：修改`_get_config_for_video`方法，当赛道配置不存在时创建默认配置

### 问题3：growth_rate未持久化
- **现象**：判定时计算的growth_rate只存在内存中，未保存到数据库
- **原因**：`is_hot_video`方法计算了新的growth_rate但没有更新数据库
- **修复**：
  1. 在`MonitorPoolService`添加`update_video_growth_rate`方法
  2. 在`is_hot_video`方法中，计算完growth_rate后调用持久化

### 修改文件
- `src/services/monitor_pool_service.py`
  - 新增`update_video_growth_rate`方法（line 323-334）
- `src/services/hot_judge.py`
  - `is_hot_video`：添加fallback逻辑
  - `is_hot_video`：添加持久化调用`self.monitor_service.update_video_growth_rate(bvid, growth_rate)`
  - `_get_config_for_video`：当配置不存在时返回默认配置
  - `should_decline_video`：使用`_get_config_for_video`
  - `get_hot_score`：使用`_get_config_for_video`

---

## 三、定时任务状态

### 调度器状态
- 调度器在后台线程运行
- `hourly_video_update_task`：每小时执行一次

### 任务流程（P0规范）

#### Step 1: 采集全量快照
- 抓取监控池视频最新数据
- 写入时序快照表（hourly_snapshot）

#### Step 2: 爆款判定（正向+逆向）

**正向处理：**
- 对入库≥24h的成熟视频执行三层判定
- 判定通过 → 维持/更新为`featured`

**逆向处理（新增）：**
- 判定不通过，且当前状态为`featured` → 降级为`monitoring`
- 确保不达标的视频不会一直占据featured位置

#### Step 3: 冷启动视频
- 入库<24h的视频不参与判定
- 无状态变更，保持原状态

### 修改文件
- `src/tasks/video_tasks.py`
  - `hourly_video_update_task`：新增逆向降级逻辑
  - 判定不通过且当前为featured → 修改状态为monitoring

### 判定结果统计（2026-07-19）

| 分类 | 数量 | 说明 |
|------|------|------|
| Featured视频总数 | 66 | 旧逻辑标记 |
| 冷启动featured(<24h) | 18 | 不参与新逻辑判定 |
| 成熟featured(≥24h) | 48 | 需重新判定 |
| 判定通过维持featured | 47 | 符合新逻辑 |
| 判定不通过降级 | 1 | BV1BCNi67EVM (growth_rate=0.0%) |
| **前端实际显示** | **65** | 18冷启动 + 47成熟通过 |

---

## 四、封面图片问题排查

### 已验证排除的故障点

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 后端API正常 | ✅ | `/api/videos/featured` 返回200，数据完整 |
| 图片URL格式 | ✅ | 已统一替换为 `https://i0.hdslb.com/xxx` |
| 图片资源可访问 | ✅ | `curl -sI https://...` 返回200 |
| 前端服务正常 | ✅ | 3003端口监听，页面返回200 |
| JSON编码正常 | ✅ | UTF-8编码，中文正常解析 |
| 前端img跨域属性 | ✅ | 已添加 `crossOrigin="anonymous"` |
| 前端重新编译 | ✅ | Next.js热更新成功 |

### 已执行的修复操作

1. **封面URL协议升级**
   - 全量更新数据库中175条记录的cover_url从`http://`改为`https://`
   - SQL: `UPDATE monitor_pool SET cover_url = REPLACE(cover_url, 'http://', 'https://')`

2. **前端跨域配置**
   - 文件：`frontend/src/app/(dashboard)/videos/page.tsx`
   - img标签添加 `crossOrigin="anonymous"` 属性

3. **前端服务重启**
   - 杀掉旧前端进程(PID 14876)
   - 重启 `npm run dev`，新进程PID 25540

### 待验证项
- 浏览器无痕模式硬刷新后封面显示效果
- F12 Network面板确认图片请求状态码

---

## 五、服务状态

### 后端
- 运行状态：正常
- 端口：8000
- PID：18312
- 调度器：已启动

### 前端
- 运行状态：正常
- 端口：3003
- PID：25540
- 访问地址：http://localhost:3003/videos

---

## 待优化项
- [ ] 无痕窗口验证封面图片显示
- [ ] F12 Network面板确认图片请求状态
- [ ] 封面图片HTTPS改造（已完成）
- [ ] 视频详情页的封面显示
- [ ] 移动端响应式布局适配
- [ ] 补充缺失的赛道配置（时尚、电影、资讯、舞蹈等）
- [ ] 滑动窗口数据累积24小时后的真实增速计算验证
- [ ] 考虑调整fallback逻辑，当滑动窗口不足时使用更合理的默认值
- [ ] 冷启动视频专属展示区域设计

## 访问地址
- 前端：http://localhost:3003/videos
- 后端API：http://localhost:8000/api/videos/featured

---

## 六、Docker 部署配置更新 (2026-07-22)

### 已完成的工作

#### 1. TypeScript 类型修复
- [x] `Video` 接口添加 `ai_analysis?: AIAnalysis` 属性 (`src/types/index.ts`)
- [x] `analysisResult` 状态类型从 `unknown` 改为 `AIAnalysis | null` (`src/app/m/analysis/page.tsx`)
- [x] `Tier` 接口添加 `unavailable?: string[]` 属性 (`src/app/m/pricing/page.tsx`)

#### 2. Next.js App Router SSG/Prerender 问题修复
- [x] `(user)/page.tsx` 添加 `export const dynamic = 'force-dynamic'` 防止静态预渲染
- [x] `m/analysis/page.tsx` 使用 Suspense wrapper 包裹使用 `useSearchParams()` 的组件
- [x] `m/pricing/page.tsx` 移除未使用的 `useSearchParams` import

#### 3. Docker 部署配置
- [x] `next.config.mjs` 添加 `output: 'standalone'`
- [x] `Dockerfile` 添加 `rm -rf .next` 在 build 前
- [x] 修复 COPY 路径: `/app/.next/standalone/frontend` → `./frontend`
- [x] 更新 CMD 为 `node frontend/server.js`

#### 4. 构建状态
- [x] 前端构建成功 (仅有 ESLint warnings，无 errors)

### 修改的文件

| 文件 | 修改内容 |
|------|----------|
| `src/types/index.ts` | 添加 ai_analysis 属性 |
| `src/app/m/analysis/page.tsx` | Suspense wrapper + 类型修复 |
| `src/app/m/pricing/page.tsx` | 移除 useSearchParams + unavailable 属性 |
| `src/app/(user)/page.tsx` | 添加 dynamic export |
| `next.config.mjs` | 添加 standalone output |
| `Dockerfile` | 修复路径和 build 步骤 |

### 服务状态检查 (2026-07-22)

| 服务 | 端口 | 状态 |
|------|------|------|
| PostgreSQL | 5432 | 运行中 |
| Redis | 6379 | 运行中 |
| 后端 API | 8000 | **未运行** |
| 前端 Next.js | 3000 | 未运行 |

### 待完成
- [ ] 启动后端服务器 (端口 8000)
- [ ] 运行 Docker build 验证容器构建
- [ ] 测试完整部署流程
