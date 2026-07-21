"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  LoginRequest,
  RegisterRequest,
  HotJudgeRequest,
} from "@/types";

// Query Keys
export const queryKeys = {
  videos: ["videos"] as const,
  video: (bvid: string) => ["video", bvid] as const,
  channels: ["channels"] as const,
  dashboardStats: ["dashboard", "stats"] as const,
  featuredVideos: ["dashboard", "featured"] as const,
  videoAnalysis: (bvid: string) => ["analysis", bvid] as const,
};

// Video Queries
export function useVideos(params?: { channel?: string; status?: string; limit?: number }) {
  return useQuery({
    queryKey: [...queryKeys.videos, params],
    queryFn: () => api.getVideos(params),
  });
}

// 已上榜视频查询（用户界面用）
export function useFeaturedVideos(params?: { channel?: string; limit?: number }) {
  return useQuery({
    queryKey: ["featured-videos", params],
    queryFn: () => api.getFeaturedVideos(params),
    refetchInterval: 60000, // 每分钟刷新
  });
}

export function useVideo(bvid: string) {
  return useQuery({
    queryKey: queryKeys.video(bvid),
    queryFn: () => api.getVideo(bvid),
    enabled: !!bvid,
  });
}

export function useJudgeVideo() {
  return useMutation({
    mutationFn: (data: HotJudgeRequest) => api.judgeVideo(data),
  });
}

// Channel Queries
export function useChannels() {
  return useQuery({
    queryKey: queryKeys.channels,
    queryFn: api.getChannels,
  });
}

export function useLockChannel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (channelId: string) => api.lockChannel(channelId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.channels });
    },
  });
}

export function useUnlockChannel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (channelId: string) => api.unlockChannel(channelId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.channels });
    },
  });
}

export function useCalibrateChannel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (channelId: string) => api.calibrateChannel(channelId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.channels });
    },
  });
}

// Dashboard Queries
export function useDashboardStats() {
  return useQuery({
    queryKey: queryKeys.dashboardStats,
    queryFn: api.getDashboardStats,
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

export function useDashboardFeaturedVideos(limit: number = 10) {
  return useQuery({
    queryKey: queryKeys.featuredVideos,
    queryFn: () => api.getFeaturedVideos({ limit }),
    refetchInterval: 60000, // Refresh every minute
  });
}

// AI Analysis Queries
export function useVideoAnalysis(bvid: string) {
  return useQuery({
    queryKey: queryKeys.videoAnalysis(bvid),
    queryFn: () => api.getVideoAnalysis(bvid),
    enabled: !!bvid,
  });
}
