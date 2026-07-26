-- 视频监控池添加当日最大在线人数字段
-- 用于记录每个视频当日的最高在线观看人数

ALTER TABLE monitor_pool ADD COLUMN IF NOT EXISTS max_online_today BIGINT DEFAULT 0;
