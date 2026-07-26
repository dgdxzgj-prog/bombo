-- Migration: Add duration and tags fields to monitor_pool and video_history tables
-- Date: 2026-07-24

-- ==================== monitor_pool ====================
-- Add duration column (in seconds)
ALTER TABLE monitor_pool ADD COLUMN IF NOT EXISTS duration INTEGER DEFAULT 0;

-- Add tags column (JSON array)
ALTER TABLE monitor_pool ADD COLUMN IF NOT EXISTS tags JSONB;

-- Create index for faster tag queries
CREATE INDEX IF NOT EXISTS idx_monitor_pool_tags ON monitor_pool USING GIN (tags);

-- Comment on columns
COMMENT ON COLUMN monitor_pool.duration IS '视频时长(秒)';
COMMENT ON COLUMN monitor_pool.tags IS '视频标签列表(JSON数组)';

-- ==================== video_history ====================
-- Add duration column (in seconds)
ALTER TABLE video_history ADD COLUMN IF NOT EXISTS duration INTEGER DEFAULT 0;

-- Add tags column (JSON array)
ALTER TABLE video_history ADD COLUMN IF NOT EXISTS tags JSONB;

-- Create index for faster tag queries
CREATE INDEX IF NOT EXISTS idx_video_history_tags ON video_history USING GIN (tags);

-- Comment on columns
COMMENT ON COLUMN video_history.duration IS '视频时长(秒)';
COMMENT ON COLUMN video_history.tags IS '视频标签列表(JSON数组)';
