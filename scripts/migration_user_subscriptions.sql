-- 用户视频订阅表
-- 用于存储用户通过关键词订阅的视频关系

CREATE TABLE IF NOT EXISTS user_video_subscriptions (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    bvid VARCHAR(20) NOT NULL,
    keyword VARCHAR(50) NOT NULL,
    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status SMALLINT DEFAULT 1,
    UNIQUE(user_id, bvid)
);

CREATE INDEX IF NOT EXISTS idx_user_video_subscriptions_user_id ON user_video_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_video_subscriptions_bvid ON user_video_subscriptions(bvid);
CREATE INDEX IF NOT EXISTS idx_user_video_subscriptions_status ON user_video_subscriptions(status);

COMMENT ON TABLE user_video_subscriptions IS '用户视频订阅表';
COMMENT ON COLUMN user_video_subscriptions.user_id IS '用户ID';
COMMENT ON COLUMN user_video_subscriptions.bvid IS '视频BV号';
COMMENT ON COLUMN user_video_subscriptions.keyword IS '订阅时使用的关键词';
COMMENT ON COLUMN user_video_subscriptions.status IS '状态: 1=监控中, 0=已取消';
