-- 用户监控池快照表
-- 用于存储用户监控池视频的小时级快照

CREATE TABLE IF NOT EXISTS user_monitor_snapshot (
    id BIGSERIAL PRIMARY KEY,
    bvid VARCHAR(20) NOT NULL,
    keyword VARCHAR(50) NOT NULL,
    view_count BIGINT DEFAULT 0,
    like_count BIGINT DEFAULT 0,
    favorite_count BIGINT DEFAULT 0,
    reply_count BIGINT DEFAULT 0,
    online_count BIGINT DEFAULT 0,
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_monitor_snapshot_bvid ON user_monitor_snapshot(bvid);
CREATE INDEX IF NOT EXISTS idx_user_monitor_snapshot_keyword ON user_monitor_snapshot(keyword);
CREATE INDEX IF NOT EXISTS idx_user_monitor_snapshot_captured_at ON user_monitor_snapshot(captured_at);

COMMENT ON TABLE user_monitor_snapshot IS '用户监控池快照表';
COMMENT ON COLUMN user_monitor_snapshot.bvid IS '视频BV号';
COMMENT ON COLUMN user_monitor_snapshot.keyword IS '视频所属关键词';
COMMENT ON COLUMN user_monitor_snapshot.captured_at IS '快照采集时间';
