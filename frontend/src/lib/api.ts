import axios, { AxiosInstance, AxiosError } from "axios";
import type {
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  VideoListResponse,
  Video,
  ChannelListResponse,
  HotJudgeRequest,
  HotJudgeResponse,
  AIAnalysisResponse,
  DashboardStats,
  FeaturedVideosResponse,
  ApiError,
} from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const createApiClient = (token?: string | null) => {
  const client: AxiosInstance = axios.create({
    baseURL: API_BASE_URL,
    headers: {
      "Content-Type": "application/json",
    },
  });

  // Add request interceptor to add auth token
  client.interceptors.request.use((config) => {
    const authToken = token || localStorage.getItem("bombo_token");
    if (authToken) {
      config.headers.Authorization = `Bearer ${authToken}`;
    }
    return config;
  });

  // Add response interceptor for error handling
  client.interceptors.response.use(
    (response) => response,
    (error: AxiosError<ApiError>) => {
      if (error.response?.status === 401) {
        // Token expired or invalid
        if (typeof window !== "undefined") {
          localStorage.removeItem("bombo_token");
          localStorage.removeItem("bombo_user");
          window.location.href = "/login";
        }
      }
      return Promise.reject(error);
    }
  );

  return client;
};

// Default API client without auto-token (for TanStack Query hooks)
const apiClient = createApiClient();

export { apiClient };

// API functions using TanStack Query patterns
export const api = {
  // Auth
  login: async (data: LoginRequest): Promise<TokenResponse> => {
    const client = createApiClient(null);
    const response = await client.post<TokenResponse>("/api/auth/login", data);
    return response.data;
  },

  register: async (data: RegisterRequest): Promise<TokenResponse> => {
    const client = createApiClient(null);
    const response = await client.post<TokenResponse>("/api/auth/register", data);
    return response.data;
  },

  logout: async (): Promise<void> => {
    const token = localStorage.getItem("bombo_token");
    if (token) {
      const client = createApiClient(token);
      await client.post("/api/auth/logout");
    }
  },

  // Videos
  getVideos: async (params?: {
    channel?: string;
    status?: string;
    limit?: number;
  }): Promise<VideoListResponse> => {
    const token = localStorage.getItem("bombo_token");
    const client = createApiClient(token);
    const response = await client.get<VideoListResponse>("/api/videos", { params });
    return response.data;
  },

  // 获取已上榜视频（用户界面用，不需要认证）
  getFeaturedVideos: async (params?: {
    channel?: string;
    limit?: number;
  }): Promise<VideoListResponse> => {
    const client = createApiClient(null);
    const response = await client.get<VideoListResponse>("/api/videos/featured", { params });
    return response.data;
  },

  getVideo: async (bvid: string): Promise<Video> => {
    const token = localStorage.getItem("bombo_token");
    const client = createApiClient(token);
    const response = await client.get<Video>(`/api/videos/${bvid}`);
    return response.data;
  },

  judgeVideo: async (data: HotJudgeRequest): Promise<HotJudgeResponse> => {
    const token = localStorage.getItem("bombo_token");
    const client = createApiClient(token);
    const response = await client.post<HotJudgeResponse>("/api/videos/judge", data);
    return response.data;
  },

  // Channels
  getChannels: async (): Promise<ChannelListResponse> => {
    const token = localStorage.getItem("bombo_token");
    const client = createApiClient(token);
    const response = await client.get<ChannelListResponse>("/api/channels");
    return response.data;
  },

  lockChannel: async (channelId: string): Promise<void> => {
    const token = localStorage.getItem("bombo_token");
    const client = createApiClient(token);
    await client.post(`/api/channels/${channelId}/lock`);
  },

  unlockChannel: async (channelId: string): Promise<void> => {
    const token = localStorage.getItem("bombo_token");
    const client = createApiClient(token);
    await client.post(`/api/channels/${channelId}/unlock`);
  },

  calibrateChannel: async (channelId: string): Promise<void> => {
    const token = localStorage.getItem("bombo_token");
    const client = createApiClient(token);
    await client.post("/api/channels/calibrate", { channel_id: channelId });
  },

  // AI Analysis
  getVideoAnalysis: async (bvid: string): Promise<AIAnalysisResponse> => {
    const token = localStorage.getItem("bombo_token");
    const client = createApiClient(token);
    const response = await client.get<AIAnalysisResponse>(`/api/ai/analysis/${bvid}`);
    return response.data;
  },

  // Dashboard
  getDashboardStats: async (): Promise<DashboardStats> => {
    const token = localStorage.getItem("bombo_token");
    const client = createApiClient(token);
    const response = await client.get<DashboardStats>("/api/dashboard/stats");
    return response.data;
  },

  // Dashboard featured videos (for dashboard page, needs auth)
  getDashboardFeaturedVideos: async (limit: number = 10): Promise<FeaturedVideosResponse> => {
    const token = localStorage.getItem("bombo_token");
    const client = createApiClient(token);
    const response = await client.get<FeaturedVideosResponse>("/api/dashboard/featured", {
      params: { limit },
    });
    return response.data;
  },
};

export default api;
