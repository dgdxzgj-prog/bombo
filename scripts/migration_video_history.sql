-- 视频历史表，用于存储从监控池清理的视频
CREATE TABLE IF NOT EXISTS video_history (
    id BIGSERIAL PRIMARY KEY,
    bvid VARCHAR(20) NOT NULL UNIQUE,
    title VARCHAR(500),
    author VARCHAR(200),
    author_mid VARCHAR(50),
    channel VARCHAR(100),
    keyword VARCHAR(100),

    -- 播放量与增速
    view_yesterday INTEGER DEFAULT 0,
    view_today INTEGER DEFAULT 0,
    growth_rate DECIMAL(10, 2) DEFAULT 0,

    -- 互动数据
    like_count INTEGER DEFAULT 0,
    favorite_count INTEGER DEFAULT 0,
    reply_count INTEGER DEFAULT 0,
    coin_count BIGINT DEFAULT 0,
    share_count BIGINT DEFAULT 0,
    danmu_count BIGINT DEFAULT 0,
    online_count INTEGER DEFAULT 0,
    max_online_today INTEGER DEFAULT 0,

    -- 视频元数据
    pubdate TIMESTAMP,
    cover_url TEXT,

    -- 状态
    status VARCHAR(20) DEFAULT 'declined',

    -- 时间戳
    first_seen TIMESTAMP,
    last_collected TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 清理信息
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 入历史表时间
    archived_reason VARCHAR(50) DEFAULT 'cleanup',    -- 入历史表原因
    last_status VARCHAR(20),                          -- 清理前最后状态
    last_channel VARCHAR(100),                        -- 清理前最后赛道

    -- 爆款追踪字段
    first_featured_at TIMESTAMP,                      -- 首次上榜时间
    max_online_ever INTEGER DEFAULT 0                 -- 历史最高在线人数
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_video_history_bvid ON video_history(bvid);
CREATE INDEX IF NOT EXISTS idx_video_history_archived_at ON video_history(archived_at);
CREATE INDEX IF NOT EXISTS idx_video_history_status ON video_history(status);

-- 评论表也需要历史记录（如果存在的话）
-- CREATE TABLE IF NOT EXISTS video_comment_history (...);