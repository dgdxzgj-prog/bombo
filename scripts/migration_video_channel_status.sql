-- 视频赛道关联表添加状态字段
-- 用于支持视频在每个赛道有不同的状态

-- 1. 添加状态字段到 video_channel 表
ALTER TABLE video_channel ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'monitoring';

-- 2. 添加 CHECK 约束限制状态值
ALTER TABLE video_channel DROP CONSTRAINT IF EXISTS video_channel_status_check;
ALTER TABLE video_channel ADD CONSTRAINT video_channel_status_check
    CHECK (status IS NULL OR status IN ('monitoring', 'featured', 'declined'));

-- 3. 将 monitor_pool.status 数据迁移到 video_channel
-- 对于 is_primary = true 的记录，同步状态
UPDATE video_channel vc
SET status = mp.status
FROM monitor_pool mp
WHERE vc.video_bvid = mp.bvid
  AND vc.is_primary = TRUE;

-- 4. 添加索引
CREATE INDEX IF NOT EXISTS idx_video_channel_status ON video_channel(status);
CREATE INDEX IF NOT EXISTS idx_video_channel_bvid_status ON video_channel(video_bvid, status);
