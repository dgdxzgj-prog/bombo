# BOMBO Frontend

B站视频热度监控系统的 Next.js 前端应用

## 技术栈

- **Framework**: Next.js 14 (App Router, SSR)
- **Language**: TypeScript
- **Styling**: TailwindCSS (暗黑主题)
- **State**: Zustand
- **Data Fetching**: TanStack Query
- **Charts**: ECharts
- **Icons**: Lucide React

## Getting Started

### 环境要求

- Node.js 18+
- npm 或 yarn

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

访问 http://localhost:3000

### 构建生产版本

```bash
npm run build
npm start
```

### Docker 部署

```bash
docker build -t bombo-frontend .
docker run -p 3000:3000 bombo-frontend
```

## 项目结构

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── (auth)/            # 认证页面
│   │   │   ├── login/
│   │   │   └── register/
│   │   ├── (dashboard)/       # 仪表盘页面
│   │   │   ├── dashboard/
│   │   │   └── videos/
│   │   ├── globals.css
│   │   └── layout.tsx
│   ├── components/             # React 组件
│   │   ├── Sidebar.tsx
│   │   ├── Header.tsx
│   │   ├── StatCard.tsx
│   │   ├── TrendChart.tsx
│   │   └── ChannelChart.tsx
│   ├── hooks/                  # TanStack Query hooks
│   │   └── useApi.ts
│   ├── lib/                    # 工具库
│   │   ├── api.ts             # API 客户端
│   │   ├── store.ts           # Zustand store
│   │   └── providers.tsx      # React Query provider
│   └── types/                  # TypeScript 类型
│       └── index.ts
├── public/
├── package.json
├── tailwind.config.ts
├── tsconfig.json
└── Dockerfile
```

## 环境变量

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 功能特性

- [x] 用户认证 (登录/注册)
- [x] 仪表盘概览
- [x] 视频列表管理
- [x] 视频详情查看
- [x] 赛道配置管理
- [x] 数据可视化 (ECharts)
- [x] 响应式设计
- [x] 暗黑主题
- [x] 权限控制

## 权限说明

| 角色 | 功能 |
|------|------|
| guest | 浏览公开信息 |
| free | 视频浏览、搜索 |
| vip | + AI分析、赛道管理 |
| admin | + 用户管理 |
