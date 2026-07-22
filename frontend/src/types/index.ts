// User types
export type UserRole = "guest" | "free" | "vip" | "admin";

export interface User {
  id: number;
  username: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  password: string;
  email: string;
}

export interface TokenResponse {
  token: string;
  user: User;
  expires_at: string;
}

// Video types
export type VideoStatus = "monitoring" | "featured" | "declined";

export interface Video {
  bvid: string;
  title: string;
  author: string;
  channel: string;
  keyword?: string;
  view_yesterday: number;
  view_today: number;
  growth_rate: number;
  like_count: number;
  favorite_count: number;
  reply_count: number;
  pubdate?: string;
  cover_url?: string;
  status: VideoStatus;
  first_seen: string;
  last_collected?: string;
  ai_analysis?: AIAnalysis;
}

export interface VideoListResponse {
  total: number;
  videos: Video[];
}

// Channel types
export interface ChannelConfig {
  channel_id: string;
  channel_name: string;
  burst_growth_threshold: number;
  burst_volume_threshold: number;
  base_growth_threshold: number;
  base_volume_threshold: number;
  cold_start_threshold: number;
  cold_start_hours: number;
  weight_growth: number;
  weight_volume: number;
  weight_interaction: number;
  decline_growth_threshold: number;
  param_version: number;
  effective_time?: string;
  sample_size: number;
  is_locked: boolean;
}

export interface ChannelListResponse {
  total: number;
  channels: ChannelConfig[];
}

// Hot Judge types
export interface HotJudgeRequest {
  bvid: string;
}

export interface HotJudgeResponse {
  is_hot: boolean;
  reason: string;
  score?: number;
}

// AI Analysis types
export interface AICoverAnalysis {
  cover_composition: string | null;
  cover_main_element: string | null;
  cover_color_scheme: string | null;
  cover_visual_style: string | null;
  cover_mood_atmosphere: string | null;
  cover_visual_highlights: string[];
  cover_audience_expectation: string | null;
}

export interface AIContentAnalysis {
  topic_summary: string | null;
  viral_logic_analysis: string | null;
  content_optimization_suggestions: string | null;
  replicability_evaluation: string | null;
}

export interface AIAnalysis {
  bvid: string;
  created_at: string | null;
  cover_analysis: AICoverAnalysis | null;
  content_analysis: AIContentAnalysis | null;
}

export interface AIAnalysisResponse {
  cached: boolean;
  analysis: AIAnalysis;
}

// Dashboard types
export interface DashboardStats {
  videos: {
    monitoring: number;
    featured: number;
    declined: number;
    total: number;
  };
  channels: {
    total: number;
    locked: number;
    unlocked: number;
  };
  timestamp: string;
}

export interface FeaturedVideosResponse {
  total: number;
  videos: Video[];
}

// API Error
export interface ApiError {
  detail: string;
}

// User Level types
export type UserLevel = "tourist" | "free" | "light" | "standard" | "pro";

// Subscription types
export interface SubscriptionTier {
  tier: string;
  name: string;
  price: number;
  features: string[];
  limits: {
    day_self_analysis: number;
    month_custom_bvid: number;
    month_compare: number;
  };
}

export interface SubscriptionOrder {
  id: number;
  user_id: number;
  tier: string;
  price: number;
  status: string;
  valid_from: string;
  valid_until: string;
  auto_renew: boolean;
}

export interface SubscriptionInfo {
  order_id?: number;
  tier?: string;
  price?: number;
  status?: string;
  valid_from?: string;
  valid_until?: string;
  auto_renew?: boolean;
}

export interface SubscribeResponse {
  success: boolean;
  order?: SubscriptionOrder;
  payment_url?: string;
}

export interface UserStatusResponse {
  user_level: UserLevel;
  is_login: boolean;
  permissions: {
    user_level: UserLevel;
    is_paid: boolean;
    tier: string | null;
    status_label: string;
    upgrade_hint: string | null;
    upgrade_tiers: Array<{ tier: string; price: number }>;
    trial_count?: number;
  };
  quotas: Record<string, unknown>;
}
