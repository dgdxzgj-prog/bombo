-- Migration: Add duration and tags fields to monitor_pool table
-- Date: 2026-07-24

-- Add duration column (in seconds)
ALTER TABLE monitor_pool ADD COLUMN IF NOT EXISTS duration INTEGER DEFAULT 0;

-- Add tags column (JSON array stored as text)
ALTER TABLE monitor_pool ADD COLUMN IF NOT EXISTS tags JSONB;

-- Create index for faster tag queries
CREATE INDEX IF NOT EXISTS idx_monitor_pool_tags ON monitor_pool USING GIN (tags);

-- Comment on columns
COMMENT ON COLUMN monitor_pool.duration IS '视频时长(秒)';
COMMENT ON COLUMN monitor_pool.tags IS '视频标签列表(JSON数组)';
