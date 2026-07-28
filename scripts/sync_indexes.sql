-- BOMBO 数据库索引同步脚本
-- 从本地同步索引到服务器
-- 执行方式: psql -h <服务器IP> -U postgres -d bombo -f sync_indexes.sql

-- ============================================
-- monitor_pool 表索引
-- ============================================
CREATE INDEX IF NOT EXISTS idx_monitor_channel ON monitor_pool(channel);
CREATE INDEX IF NOT EXISTS idx_monitor_status ON monitor_pool(status);
CREATE INDEX IF NOT EXISTS idx_monitor_growth ON monitor_pool(growth_rate DESC);
CREATE INDEX IF NOT EXISTS idx_monitor_bvid ON monitor_pool(bvid);
CREATE INDEX IF NOT EXISTS idx_monitor_created ON monitor_pool(created_at);
CREATE INDEX IF NOT EXISTS idx_monitor_author_mid ON monitor_pool(author_mid);
CREATE INDEX IF NOT EXISTS idx_monitor_need_author_collect ON monitor_pool(need_author_collect) WHERE need_author_collect = TRUE;

-- ============================================
-- channel_config 表索引
-- ============================================
CREATE INDEX IF NOT EXISTS idx_channel_name ON channel_config(channel_name);
CREATE INDEX IF NOT EXISTS idx_channel_locked ON channel_config(is_locked);

-- ============================================
-- ai_cache 表索引
-- ============================================
CREATE INDEX IF NOT EXISTS idx_ai_cache_bvid ON ai_cache(bvid);
CREATE INDEX IF NOT EXISTS idx_ai_cache_expires ON ai_cache(expires_at);

-- ============================================
-- hourly_snapshot 表索引
-- ============================================
CREATE INDEX IF NOT EXISTS idx_snapshot_bvid ON hourly_snapshot(bvid);
CREATE INDEX IF NOT EXISTS idx_snapshot_time ON hourly_snapshot(snapshot_time);
CREATE INDEX IF NOT EXISTS idx_snapshot_bvid_time ON hourly_snapshot(bvid, snapshot_time DESC);

-- ============================================
-- daily_hot 表索引
-- ============================================
CREATE INDEX IF NOT EXISTS idx_daily_rank ON daily_hot(rank);
CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_hot(analysis_date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_bvid ON daily_hot(bvid);

-- ============================================
-- author_info 表索引
-- ============================================
CREATE INDEX IF NOT EXISTS idx_author_mid ON author_info(mid);
CREATE INDEX IF NOT EXISTS idx_author_fans ON author_info(fans DESC);

-- ============================================
-- author_collect_lock 表索引
-- ============================================
-- (锁表通常不需要额外索引)

-- ============================================
-- track_online_history 表索引
-- ============================================
CREATE INDEX IF NOT EXISTS idx_track_online_channel ON track_online_history(channel_id);
CREATE INDEX IF NOT EXISTS idx_track_online_date ON track_online_history(channel_id, stat_date);
CREATE INDEX IF NOT EXISTS idx_track_online_bvid ON track_online_history(bvid);

-- ============================================
-- video_channel 表索引
-- ============================================
CREATE INDEX IF NOT EXISTS idx_video_channel_bvid ON video_channel(video_bvid);
CREATE INDEX IF NOT EXISTS idx_video_channel_channel_id ON video_channel(channel_id);
CREATE INDEX IF NOT EXISTS idx_video_channel_status ON video_channel(status);
CREATE INDEX IF NOT EXISTS idx_video_channel_bvid_status ON video_channel(video_bvid, status);

-- ============================================
-- users 表索引
-- ============================================
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- ============================================
-- user_custom_channel 表索引
-- ============================================
-- (主键索引已存在)

-- ============================================
-- video_history 表索引
-- ============================================
CREATE INDEX IF NOT EXISTS idx_video_history_bvid ON video_history(bvid);
CREATE INDEX IF NOT EXISTS idx_video_history_status ON video_history(status);
CREATE INDEX IF NOT EXISTS idx_video_history_archived_at ON video_history(archived_at);
CREATE INDEX IF NOT EXISTS idx_video_history_tags ON video_history USING gin(tags);

-- ============================================
-- hourly_data 表索引
-- ============================================
CREATE INDEX IF NOT EXISTS idx_hourly_bvid ON hourly_data(bvid);
CREATE INDEX IF NOT EXISTS idx_hourly_recorded ON hourly_data(recorded_at);
CREATE INDEX IF NOT EXISTS idx_hourly_bvid_recorded ON hourly_data(bvid, recorded_at);

-- ============================================
-- 其他业务表索引
-- ============================================
CREATE INDEX IF NOT EXISTS idx_cost_log_created ON ai_cost_log(created_at);
CREATE INDEX IF NOT EXISTS idx_cost_log_type ON ai_cost_log(analysis_type);
CREATE INDEX IF NOT EXISTS idx_cost_log_user ON ai_cost_log(user_id);

CREATE INDEX IF NOT EXISTS idx_order_status ON subscribe_order(status);
CREATE INDEX IF NOT EXISTS idx_order_user ON subscribe_order(user_id);
CREATE INDEX IF NOT EXISTS idx_order_valid_until ON subscribe_order(valid_until);

CREATE INDEX IF NOT EXISTS idx_user_quota_user ON user_quota(user_id);
CREATE INDEX IF NOT EXISTS idx_user_quota_period ON user_quota(period_start, period_end);

CREATE INDEX IF NOT EXISTS idx_pop_log_created ON transform_pop_log(created_at);
CREATE INDEX IF NOT EXISTS idx_pop_log_type ON transform_pop_log(pop_type);
CREATE INDEX IF NOT EXISTS idx_pop_log_user ON transform_pop_log(user_id);

CREATE INDEX IF NOT EXISTS idx_track_rid_rid ON track_rid_mapping(rid);

-- ============================================
-- 验证索引创建
-- ============================================
-- SELECT indexname, tablename FROM pg_indexes WHERE schemaname = 'public' ORDER BY tablename, indexname;
