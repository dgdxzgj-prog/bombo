-- BOMBO 数据库迁移脚本 V2
-- 版本: V2.0
-- 日期: 2026-07-21
-- 说明: 新增用户分层、订阅、额度管理相关表

-- ============================================
-- 1. 扩展用户表新增字段
-- ============================================
ALTER TABLE users ADD COLUMN IF NOT EXISTS user_level VARCHAR(20) DEFAULT 'free'
    CHECK (user_level IN ('tourist', 'free', 'light', 'standard', 'pro'));
ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_count INT DEFAULT 3;  -- 游客剩余试用次数
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscribe_expire TIMESTAMP;  -- 订阅到期时间
ALTER TABLE users ADD COLUMN IF NOT EXISTS subscribe_tier VARCHAR(20) DEFAULT NULL  -- 当前订阅套餐
    CHECK (subscribe_tier IN ('light', 'standard', 'pro') or subscribe_tier IS NULL);

-- ============================================
-- 2. 用户额度表 user_quota（按月重置）
-- ============================================
CREATE TABLE IF NOT EXISTS user_quota (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    quota_type          VARCHAR(30) NOT NULL,  -- day_self_analysis / month_custom_bvid / month_compare_diagnose
    used_count          INT DEFAULT 0,
    total_count         INT DEFAULT 0,
    period_start        TIMESTAMP NOT NULL,    -- 周期开始时间
    period_end          TIMESTAMP NOT NULL,     -- 周期结束时间
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uk_user_quota_type_period UNIQUE (user_id, quota_type, period_start)
);

CREATE INDEX IF NOT EXISTS idx_user_quota_user ON user_quota(user_id);
CREATE INDEX IF NOT EXISTS idx_user_quota_period ON user_quota(period_start, period_end);

-- ============================================
-- 3. 订阅订单表 subscribe_order
-- ============================================
CREATE TABLE IF NOT EXISTS subscribe_order (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tier                VARCHAR(20) NOT NULL CHECK (tier IN ('light', 'standard', 'pro')),
    price               DECIMAL(10, 2) NOT NULL,
    status              VARCHAR(20) DEFAULT 'pending'  -- pending / paid / cancelled / expired
                    CHECK (status IN ('pending', 'paid', 'cancelled', 'expired')),
    payment_method      VARCHAR(20),  -- wechat / alipay / card
    transaction_id      VARCHAR(100),  -- 支付平台交易号
    valid_from          TIMESTAMP NOT NULL,
    valid_until         TIMESTAMP NOT NULL,
    auto_renew         BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_order_user ON subscribe_order(user_id);
CREATE INDEX IF NOT EXISTS idx_order_status ON subscribe_order(status);
CREATE INDEX IF NOT EXISTS idx_order_valid_until ON subscribe_order(valid_until);

-- ============================================
-- 4. AI成本日志表 ai_cost_log
-- ============================================
CREATE TABLE IF NOT EXISTS ai_cost_log (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT REFERENCES users(id) ON DELETE SET NULL,
    bvid                VARCHAR(20),
    analysis_type       VARCHAR(50) NOT NULL,  -- cover_analysis / content_analysis / frame_extract / compare_diagnose / commercial_report
    input_tokens        INT DEFAULT 0,
    output_tokens       INT DEFAULT 0,
    input_cost          DECIMAL(10, 6) DEFAULT 0,   -- 输入成本(元)
    output_cost         DECIMAL(10, 6) DEFAULT 0,   -- 输出成本(元)
    total_cost          DECIMAL(10, 6) DEFAULT 0,   -- 总成本(元)
    duration_ms         INT DEFAULT 0,              -- 耗时毫秒
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cost_log_user ON ai_cost_log(user_id);
CREATE INDEX IF NOT EXISTS idx_cost_log_type ON ai_cost_log(analysis_type);
CREATE INDEX IF NOT EXISTS idx_cost_log_created ON ai_cost_log(created_at);

-- ============================================
-- 5. 权限配置表 permission_config
-- ============================================
CREATE TABLE IF NOT EXISTS permission_config (
    id                  BIGSERIAL PRIMARY KEY,
    tier                VARCHAR(20) NOT NULL CHECK (tier IN ('tourist', 'free', 'light', 'standard', 'pro')),
    permission_key      VARCHAR(50) NOT NULL,
    permission_value    VARCHAR(100) NOT NULL,
    description         TEXT,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uk_tier_permission UNIQUE (tier, permission_key)
);

-- 插入默认权限配置
INSERT INTO permission_config (tier, permission_key, permission_value, description) VALUES
-- 游客
('tourist', 'trial_count', '3', '游客免费试用次数'),
('tourist', 'video_list_limit', '40', '榜单可见条数'),
('tourist', 'ai_analysis_limit', '32', '基础AI分析条数限制'),
('tourist', 'allow_frame_extract', 'false', '是否允许抽帧分析'),
('tourist', 'allow_custom_bvid', 'false', '是否允许自定义BVID分析'),
('tourist', 'allow_compare_diagnose', 'false', '是否允许对标诊断'),
('tourist', 'allow_commercial_report', 'false', '是否允许商业化报告'),
-- 免费用户
('free', 'video_list_limit', '999999', '榜单可见条数(不限制)'),
('free', 'ai_analysis_limit', '32', '基础AI分析条数限制'),
('free', 'day_self_analysis_quota', '0', '每日自选分析额度'),
('free', 'month_custom_bvid_quota', '0', '月度自定义BVID额度'),
('free', 'month_compare_quota', '0', '月度对标诊断额度'),
('free', 'allow_frame_extract', 'false', '是否允许抽帧分析'),
('free', 'allow_custom_bvid', 'false', '是否允许自定义BVID分析'),
('free', 'allow_compare_diagnose', 'false', '是否允许对标诊断'),
('free', 'allow_commercial_report', 'false', '是否允许商业化报告'),
-- 轻量版
('light', 'video_list_limit', '999999', '榜单可见条数(不限制)'),
('light', 'ai_analysis_limit', '40', '基础AI分析条数限制'),
('light', 'day_self_analysis_quota', '10', '每日自选分析额度'),
('light', 'month_custom_bvid_quota', '0', '月度自定义BVID额度'),
('light', 'month_compare_quota', '0', '月度对标诊断额度'),
('light', 'allow_frame_extract', 'true', '是否允许抽帧分析'),
('light', 'allow_custom_bvid', 'false', '是否允许自定义BVID分析'),
('light', 'allow_compare_diagnose', 'false', '是否允许对标诊断'),
('light', 'allow_commercial_report', 'false', '是否允许商业化报告'),
-- 标准版
('standard', 'video_list_limit', '999999', '榜单可见条数(不限制)'),
('standard', 'ai_analysis_limit', '999999', '基础AI分析条数限制(不限制)'),
('standard', 'day_self_analysis_quota', '10', '每日自选分析额度'),
('standard', 'month_custom_bvid_quota', '150', '月度自定义BVID额度'),
('standard', 'month_compare_quota', '30', '月度对标诊断额度'),
('standard', 'allow_frame_extract', 'true', '是否允许抽帧分析'),
('standard', 'allow_custom_bvid', 'true', '是否允许自定义BVID分析'),
('standard', 'allow_compare_diagnose', 'true', '是否允许对标诊断'),
('standard', 'allow_commercial_report', 'false', '是否允许商业化报告'),
-- 专业版
('pro', 'video_list_limit', '999999', '榜单可见条数(不限制)'),
('pro', 'ai_analysis_limit', '999999', '基础AI分析条数限制(不限制)'),
('pro', 'day_self_analysis_quota', '999999', '每日自选分析额度(不限制)'),
('pro', 'month_custom_bvid_quota', '500', '月度自定义BVID额度'),
('pro', 'month_compare_quota', '100', '月度对标诊断额度'),
('pro', 'allow_frame_extract', 'true', '是否允许抽帧分析'),
('pro', 'allow_custom_bvid', 'true', '是否允许自定义BVID分析'),
('pro', 'allow_compare_diagnose', 'true', '是否允许对标诊断'),
('pro', 'allow_commercial_report', 'true', '是否允许商业化报告')
ON CONFLICT (tier, permission_key) DO NOTHING;

-- ============================================
-- 6. 弹窗转化埋点表 transform_pop_log
-- ============================================
CREATE TABLE IF NOT EXISTS transform_pop_log (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             BIGINT REFERENCES users(id) ON DELETE SET NULL,
    pop_type            VARCHAR(30) NOT NULL,  -- trial_exhausted / free_upgrade / light_upgrade / standard_upgrade / pro_upgrade
    tier_target         VARCHAR(20),            -- 目标套餐
    clicked              BOOLEAN DEFAULT FALSE,  -- 是否点击了升级按钮
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pop_log_user ON transform_pop_log(user_id);
CREATE INDEX IF NOT EXISTS idx_pop_log_type ON transform_pop_log(pop_type);
CREATE INDEX IF NOT EXISTS idx_pop_log_created ON transform_pop_log(created_at);
