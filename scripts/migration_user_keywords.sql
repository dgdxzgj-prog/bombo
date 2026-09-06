-- 自选赛道用户关键词表
-- 用于存储用户添加的自定义关键词

CREATE TABLE IF NOT EXISTS user_keywords (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    keyword VARCHAR(50) NOT NULL,
    channel VARCHAR(50) DEFAULT '其他',
    status SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, keyword)
);

CREATE INDEX IF NOT EXISTS idx_user_keywords_user_id ON user_keywords(user_id);
CREATE INDEX IF NOT EXISTS idx_user_keywords_status ON user_keywords(status);

COMMENT ON TABLE user_keywords IS '用户自选赛道关键词表';
COMMENT ON COLUMN user_keywords.user_id IS '用户ID';
COMMENT ON COLUMN user_keywords.keyword IS '关键词';
COMMENT ON COLUMN user_keywords.channel IS '归类到的标准赛道';
COMMENT ON COLUMN user_keywords.status IS '状态: 1=监控中, 0=已停用';
