-- 赛道自适应爆款判定算法 - 数据库变更
-- 添加阈值计算相关字段

-- 1. 给 channel_config 添加赛道自适应阈值相关字段
ALTER TABLE channel_config ADD COLUMN IF NOT EXISTS p_up DECIMAL(5,4) DEFAULT 0.90;
ALTER TABLE channel_config ADD COLUMN IF NOT EXISTS p_down DECIMAL(5,4) DEFAULT 0.70;
ALTER TABLE channel_config ADD COLUMN IF NOT EXISTS hysteresis_ratio DECIMAL(5,4) DEFAULT 0.75;
ALTER TABLE channel_config ADD COLUMN IF NOT EXISTS window_days INT DEFAULT 14;
ALTER TABLE channel_config ADD COLUMN IF NOT EXISTS min_sample_count INT DEFAULT 30;
ALTER TABLE channel_config ADD COLUMN IF NOT EXISTS t_up BIGINT DEFAULT 0;
ALTER TABLE channel_config ADD COLUMN IF NOT EXISTS t_down BIGINT DEFAULT 0;
ALTER TABLE channel_config ADD COLUMN IF NOT EXISTS t_up_min BIGINT DEFAULT 100;
ALTER TABLE channel_config ADD COLUMN IF NOT EXISTS t_down_min BIGINT DEFAULT 50;
ALTER TABLE channel_config ADD COLUMN IF NOT EXISTS last_threshold_update TIMESTAMP;
ALTER TABLE channel_config ADD COLUMN IF NOT EXISTS threshold_sample_count INT DEFAULT 0;

-- 2. 添加视频首次上榜时间字段（用于判断是否满24小时）
ALTER TABLE monitor_pool ADD COLUMN IF NOT EXISTS first_featured_at TIMESTAMP;

-- 3. 添加视频最大在线历史峰值（整个生命周期）
ALTER TABLE monitor_pool ADD COLUMN IF NOT EXISTS max_online_ever BIGINT DEFAULT 0;

-- 4. 创建赛道视频峰值在线历史表（用于统计分位数）
CREATE TABLE IF NOT EXISTS track_online_history (
    id              BIGSERIAL PRIMARY KEY,
    channel_id      VARCHAR(50) NOT NULL,
    bvid            VARCHAR(20) NOT NULL,
    max_online      BIGINT NOT NULL,
    stat_date       DATE NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_track_online_channel ON track_online_history(channel_id);
CREATE INDEX IF NOT EXISTS idx_track_online_date ON track_online_history(channel_id, stat_date);
CREATE INDEX IF NOT EXISTS idx_track_online_bvid ON track_online_history(bvid);
