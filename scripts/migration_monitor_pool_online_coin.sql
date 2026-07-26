-- monitor_pool添加在线人数和投币数字段
-- 用于前端直接从monitor_pool读取数据

-- 添加在线人数字段
ALTER TABLE monitor_pool ADD COLUMN IF NOT EXISTS online_count BIGINT DEFAULT 0;

-- 添加投币数字段
ALTER TABLE monitor_pool ADD COLUMN IF NOT EXISTS coin_count BIGINT DEFAULT 0;

-- 添加分享数字段
ALTER TABLE monitor_pool ADD COLUMN IF NOT EXISTS share_count BIGINT DEFAULT 0;

-- 添加弹幕数字段
ALTER TABLE monitor_pool ADD COLUMN IF NOT EXISTS danmu_count BIGINT DEFAULT 0;
