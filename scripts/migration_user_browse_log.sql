-- 用户浏览记录表
-- 用于记录用户浏览视频的行为，统计用户浏览趋势

CREATE TABLE IF NOT EXISTS user_browse_log (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    bvid VARCHAR(20) NOT NULL,
    browse_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_user_browse_log_user_id ON user_browse_log(user_id);
CREATE INDEX IF NOT EXISTS idx_user_browse_log_browse_time ON user_browse_log(browse_time);
