-- UP主信息采集控制字段
-- 用于控制是否需要对视频的UP主信息进行采集

-- 给monitor_pool表添加UP主采集控制字段
ALTER TABLE monitor_pool ADD COLUMN IF NOT EXISTS need_author_collect BOOLEAN DEFAULT FALSE;

-- 添加索引加速查询
CREATE INDEX IF NOT EXISTS idx_monitor_need_author_collect ON monitor_pool(need_author_collect) WHERE need_author_collect = TRUE;

-- 作者信息采集锁表（用于确保只有一个进程执行采集）
CREATE TABLE IF NOT EXISTS author_collect_lock (
    id              SERIAL PRIMARY KEY,
    lock_name       VARCHAR(100) NOT NULL UNIQUE,
    locked_by       VARCHAR(200),
    locked_at       TIMESTAMP,
    expires_at      TIMESTAMP
);

-- 插入默认锁记录
INSERT INTO author_collect_lock (lock_name, locked_by, locked_at, expires_at)
VALUES ('author_collect', NULL, NULL, NULL)
ON CONFLICT (lock_name) DO NOTHING;