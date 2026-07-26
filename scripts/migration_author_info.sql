-- UP主信息表 (author_info)
-- 存储UP主基本信息、粉丝数、作品数等
CREATE TABLE IF NOT EXISTS author_info (
    -- 主键与基础信息
    id              BIGSERIAL PRIMARY KEY,
    mid             VARCHAR(50) NOT NULL UNIQUE,
    name            VARCHAR(200),
    avatar          TEXT,

    -- 粉丝与关注数据
    fans            BIGINT DEFAULT 0,           -- 粉丝数
    following       BIGINT DEFAULT 0,           -- 关注数

    -- 作品统计
    archive_count   BIGINT DEFAULT 0,           -- 投稿作品数（审核通过）

    -- 扩展统计
    total_view      BIGINT DEFAULT 0,           -- 总播放
    total_liked     BIGINT DEFAULT 0,           -- 总获赞

    -- 时间戳
    first_collected TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_author_mid ON author_info(mid);
CREATE INDEX IF NOT EXISTS idx_author_fans ON author_info(fans DESC);

-- 给monitor_pool表添加作者关联字段
ALTER TABLE monitor_pool ADD COLUMN IF NOT EXISTS author_mid VARCHAR(50);
CREATE INDEX IF NOT EXISTS idx_monitor_author_mid ON monitor_pool(author_mid);

-- 可选：添加外键约束（如果author_info已存在）
-- ALTER TABLE monitor_pool ADD CONSTRAINT fk_author_mid FOREIGN KEY (author_mid) REFERENCES author_info(mid);