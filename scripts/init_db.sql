-- BOMBO 数据库初始化脚本
-- 版本: V1.0
-- 日期: 2026-07-16

-- 创建数据库（如果不存在）
-- CREATE DATABASE bombo;

-- ============================================
-- 监控池主表 (monitor_pool)
-- ============================================
CREATE TABLE IF NOT EXISTS monitor_pool (
    -- 主键与基础信息
    id              BIGSERIAL PRIMARY KEY,
    bvid            VARCHAR(20) NOT NULL UNIQUE,
    title           VARCHAR(500),
    author          VARCHAR(200),
    channel         VARCHAR(100) NOT NULL,
    keyword         VARCHAR(200),

    -- 播放量与增速
    view_yesterday  BIGINT DEFAULT 0,
    view_today      BIGINT DEFAULT 0,
    growth_rate     DECIMAL(10, 2) DEFAULT 0.00,

    -- 互动数据
    like_count      BIGINT DEFAULT 0,
    favorite_count  BIGINT DEFAULT 0,
    reply_count     BIGINT DEFAULT 0,

    -- 视频元数据
    pubdate         TIMESTAMP,
    cover_url       TEXT,

    -- 状态管理
    status          VARCHAR(20) DEFAULT 'monitoring'
                    CHECK (status IN ('monitoring', 'featured', 'declined')),

    -- 时间戳
    first_seen      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_collected  TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_monitor_channel ON monitor_pool(channel);
CREATE INDEX IF NOT EXISTS idx_monitor_status ON monitor_pool(status);
CREATE INDEX IF NOT EXISTS idx_monitor_growth ON monitor_pool(growth_rate DESC);
CREATE INDEX IF NOT EXISTS idx_monitor_bvid ON monitor_pool(bvid);
CREATE INDEX IF NOT EXISTS idx_monitor_created ON monitor_pool(created_at);

-- ============================================
-- 赛道自适应参数配置表 (channel_config)
-- ============================================
CREATE TABLE IF NOT EXISTS channel_config (
    channel_id              VARCHAR(100) PRIMARY KEY,
    channel_name            VARCHAR(200) NOT NULL,

    -- 爆发层参数
    burst_growth_threshold  DECIMAL(10, 2),  -- 爆发增速阈值
    burst_volume_threshold  BIGINT,          -- 播放量基线阈值

    -- 体量兜底层参数
    base_growth_threshold   DECIMAL(10, 2),  -- 兜底增速阈值
    base_volume_threshold   BIGINT,          -- 兜底播放量阈值

    -- 冷启动参数
    cold_start_threshold    BIGINT,          -- 冷启动播放量阈值
    cold_start_hours        INT DEFAULT 72,  -- 冷启动时间窗口

    -- 综合评分权重
    weight_growth           DECIMAL(5, 4) DEFAULT 0.4,
    weight_volume           DECIMAL(5, 4) DEFAULT 0.3,
    weight_interaction      DECIMAL(5, 4) DEFAULT 0.3,

    -- 衰退阈值
    decline_growth_threshold DECIMAL(10, 2), -- 衰退增速阈值

    -- 参数版本管理
    param_version           INT DEFAULT 1,
    effective_time          TIMESTAMP,
    sample_size             INT DEFAULT 0,
    is_locked               BOOLEAN DEFAULT FALSE,

    -- 时间戳
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_channel_name ON channel_config(channel_name);
CREATE INDEX IF NOT EXISTS idx_channel_locked ON channel_config(is_locked);

-- ============================================
-- AI分析缓存表 (ai_cache) - 永久有效
-- ============================================
CREATE TABLE IF NOT EXISTS ai_cache (
    id              BIGSERIAL PRIMARY KEY,
    bvid            VARCHAR(20) NOT NULL,
    analysis_type   VARCHAR(50) NOT NULL,
    result_data     JSONB,
    cached_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uk_ai_cache_bvid_type UNIQUE (bvid, analysis_type)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_ai_cache_bvid ON ai_cache(bvid);

-- ============================================
-- 小时粒度快照表 (hourly_snapshot)
-- ============================================
CREATE TABLE IF NOT EXISTS hourly_snapshot (
    id              BIGSERIAL PRIMARY KEY,
    bvid            VARCHAR(20) NOT NULL,
    snapshot_time   TIMESTAMP NOT NULL,
    view_count      BIGINT NOT NULL,
    like_count      BIGINT DEFAULT 0,
    favorite_count  BIGINT DEFAULT 0,
    reply_count     BIGINT DEFAULT 0,
    coin_count      BIGINT DEFAULT 0,
    share_count     BIGINT DEFAULT 0,
    danmu_count     BIGINT DEFAULT 0,
    online_count    BIGINT DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_hourly_bvid FOREIGN KEY (bvid) REFERENCES monitor_pool(bvid),
    CONSTRAINT uk_hourly_bvid_time UNIQUE (bvid, snapshot_time)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_hourly_bvid ON hourly_snapshot(bvid);
CREATE INDEX IF NOT EXISTS idx_hourly_snapshot_time ON hourly_snapshot(snapshot_time);
CREATE INDEX IF NOT EXISTS idx_hourly_bvid_time ON hourly_snapshot(bvid, snapshot_time);

-- ============================================
-- 每日热门汇总表 (daily_hot)
-- ============================================
CREATE TABLE IF NOT EXISTS daily_hot (
    id              BIGSERIAL PRIMARY KEY,
    bvid            VARCHAR(20) NOT NULL,
    rank            INT NOT NULL,
    growth_rate     DECIMAL(10, 2),
    hot_score       DECIMAL(10, 2),
    analysis_date   DATE NOT NULL,
    ai_summary      JSONB,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_daily_bvid FOREIGN KEY (bvid) REFERENCES monitor_pool(bvid),
    CONSTRAINT uk_daily_bvid_date UNIQUE (bvid, analysis_date)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_daily_rank ON daily_hot(rank);
CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_hot(analysis_date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_bvid ON daily_hot(bvid);

-- ============================================
-- 用户表 (users) - 预留
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id              BIGSERIAL PRIMARY KEY,
    username        VARCHAR(50) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    email           VARCHAR(100),
    role            VARCHAR(20) DEFAULT 'free'
                    CHECK (role IN ('guest', 'free', 'vip', 'admin')),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- ============================================
-- 插入21个标准赛道配置（统一阈值）
-- ============================================
INSERT INTO channel_config (channel_id, channel_name, is_locked) VALUES
    ('animation', '动画', FALSE),
    ('music', '音乐', FALSE),
    ('gaming', '游戏', FALSE),
    ('entertainment', '娱乐', FALSE),
    ('film', '影视', FALSE),
    ('bangumi', '番剧', FALSE),
    ('movie', '电影', FALSE),
    ('kichiku', '鬼畜', FALSE),
    ('dance', '舞蹈', FALSE),
    ('life', '生活', FALSE),
    ('guochuang', '国创', FALSE),
    ('documentary', '纪录片', FALSE),
    ('tech', '科技', FALSE),
    ('information', '资讯', FALSE),
    ('knowledge', '知识', FALSE),
    ('food', '美食', FALSE),
    ('animal', '动物圈', FALSE),
    ('auto', '汽车', FALSE),
    ('sports', '运动', FALSE),
    ('fashion', '时尚', FALSE),
    ('software', '软件应用', FALSE)
ON CONFLICT (channel_id) DO NOTHING;
