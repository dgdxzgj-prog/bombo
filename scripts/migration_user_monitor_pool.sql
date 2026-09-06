-- 用户自选赛道监控池表
-- 独立于现有的 monitor_pool 表，用于存储用户自选赛道的视频数据

CREATE TABLE IF NOT EXISTS user_monitor_pool (
    id BIGSERIAL PRIMARY KEY,
    bvid VARCHAR(20) NOT NULL UNIQUE,
    title VARCHAR(500),
    author VARCHAR(200),
    author_mid VARCHAR(50),
    channel VARCHAR(50) DEFAULT '其他',
    keyword VARCHAR(50) NOT NULL,
    view_yesterday BIGINT DEFAULT 0,
    view_today BIGINT DEFAULT 0,
    growth_rate DECIMAL(10,4) DEFAULT 0,
    like_count BIGINT DEFAULT 0,
    favorite_count BIGINT DEFAULT 0,
    reply_count BIGINT DEFAULT 0,
    coin_count BIGINT DEFAULT 0,
    share_count BIGINT DEFAULT 0,
    danmu_count BIGINT DEFAULT 0,
    online_count BIGINT DEFAULT 0,
    max_online_today BIGINT DEFAULT 0,
    pubdate TIMESTAMP,
    cover_url TEXT,
    duration INTEGER DEFAULT 0,
    tags TEXT,
    status VARCHAR(20) DEFAULT 'monitoring',
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_collected TIMESTAMP,
    featured_at TIMESTAMP,
    declined_at TIMESTAMP,
    declined_reason VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_monitor_pool_status ON user_monitor_pool(status);
CREATE INDEX IF NOT EXISTS idx_user_monitor_pool_keyword ON user_monitor_pool(keyword);
CREATE INDEX IF NOT EXISTS idx_user_monitor_pool_channel ON user_monitor_pool(channel);
CREATE INDEX IF NOT EXISTS idx_user_monitor_pool_first_seen ON user_monitor_pool(first_seen);
CREATE INDEX IF NOT EXISTS idx_user_monitor_pool_max_online_today ON user_monitor_pool(max_online_today);

COMMENT ON TABLE user_monitor_pool IS '用户自选赛道监控池';
COMMENT ON COLUMN user_monitor_pool.bvid IS '视频BV号';
COMMENT ON COLUMN user_monitor_pool.keyword IS '发现该视频的关键词';
COMMENT ON COLUMN user_monitor_pool.status IS '状态: monitoring/featured/declined';
COMMENT ON COLUMN user_monitor_pool.featured_at IS '最近一次上榜时间';
COMMENT ON COLUMN user_monitor_pool.declined_at IS '衰退时间';
COMMENT ON COLUMN user_monitor_pool.declined_reason IS '衰退原因';
