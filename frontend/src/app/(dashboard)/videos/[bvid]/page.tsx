"use client";

import { use } from "react";
import Link from "next/link";
import { useVideo, useJudgeVideo } from "@/hooks/useApi";
import { Header } from "@/components/Header";
import { TrendChart } from "@/components/TrendChart";
import { ArrowLeft, TrendingUp, TrendingDown, Eye, ThumbsUp, MessageSquare, Sparkles, Loader2 } from "lucide-react";
import clsx from "clsx";

export default function VideoDetailPage({ params }: { params: Promise<{ bvid: string }> }) {
  const { bvid } = use(params);
  const { data: video, isLoading, error } = useVideo(bvid);
  const judgeMutation = useJudgeVideo();
  // AI分析数据直接从video.ai_analysis获取（来自/api/videos/{bvid}）
  const aiAnalysis = video?.ai_analysis;

  if (isLoading) {
    return (
      <>
        <Header title="视频详情" />
        <div className="p-6 flex items-center justify-center h-64">
          <div className="animate-pulse text-dark-textMuted">加载中...</div>
        </div>
      </>
    );
  }

  if (error || !video) {
    return (
      <>
        <Header title="视频详情" />
        <div className="p-6 flex items-center justify-center h-64">
          <div className="text-red-400">视频不存在或加载失败</div>
        </div>
      </>
    );
  }

  const handleJudge = async () => {
    try {
      await judgeMutation.mutateAsync({ bvid: video.bvid });
    } catch (err) {
      console.error("Judge failed:", err);
    }
  };

  // Mock trend data
  const trendData = [video.view_yesterday, video.view_today * 0.9, video.view_today];
  const trendLabels = ["昨日", "今日(估算)", "今日"];

  return (
    <>
      <Header title="视频详情" subtitle={video.bvid} />

      <div className="p-6 space-y-6">
        {/* Back Link */}
        <Link
          href="/videos"
          className="inline-flex items-center gap-2 text-dark-textMuted hover:text-white transition"
        >
          <ArrowLeft className="w-4 h-4" />
          返回视频列表
        </Link>

        {/* Video Info Card */}
        <div className="card p-6">
          <div className="flex flex-col lg:flex-row gap-6">
            {/* Video Thumbnail */}
            {video.cover_url && (
              <div className="w-full lg:w-64 aspect-video bg-dark-bg rounded-lg overflow-hidden flex-shrink-0">
                <img
                  src={video.cover_url}
                  alt={video.title}
                  className="w-full h-full object-cover"
                />
              </div>
            )}

            {/* Video Details */}
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-white mb-2">
                {video.title}
                <a
                  href={`https://www.bilibili.com/video/${video.bvid}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ml-2 text-sm text-blue-400 hover:text-blue-300 inline-flex items-center gap-1"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                  B站链接
                </a>
              </h1>
              <p className="text-dark-textMuted mb-4">作者: {video.author}</p>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-dark-bg p-4 rounded-lg">
                  <div className="flex items-center gap-2 text-dark-textMuted mb-1">
                    <Eye className="w-4 h-4" />
                    <span className="text-sm">播放量</span>
                  </div>
                  <p className="text-2xl font-bold text-white">
                    {video.view_today.toLocaleString()}
                  </p>
                </div>

                <div className="bg-dark-bg p-4 rounded-lg">
                  <div className="flex items-center gap-2 text-dark-textMuted mb-1">
                    {video.growth_rate >= 0 ? (
                      <TrendingUp className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <TrendingDown className="w-4 h-4 text-red-400" />
                    )}
                    <span className="text-sm">增速</span>
                  </div>
                  <p
                    className={clsx(
                      "text-2xl font-bold",
                      video.growth_rate >= 0 ? "text-emerald-400" : "text-red-400"
                    )}
                  >
                    {video.growth_rate >= 0 ? "+" : ""}
                    {video.growth_rate}%
                  </p>
                </div>

                <div className="bg-dark-bg p-4 rounded-lg">
                  <div className="flex items-center gap-2 text-dark-textMuted mb-1">
                    <ThumbsUp className="w-4 h-4" />
                    <span className="text-sm">点赞</span>
                  </div>
                  <p className="text-2xl font-bold text-white">
                    {video.like_count.toLocaleString()}
                  </p>
                </div>

                <div className="bg-dark-bg p-4 rounded-lg">
                  <div className="flex items-center gap-2 text-dark-textMuted mb-1">
                    <MessageSquare className="w-4 h-4" />
                    <span className="text-sm">评论</span>
                  </div>
                  <p className="text-2xl font-bold text-white">
                    {video.reply_count.toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Status and Judge */}
        <div className="card p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <span
                className={clsx(
                  "px-3 py-1 rounded text-sm font-medium",
                  video.status === "featured" &&
                    "bg-emerald-600/20 text-emerald-400",
                  video.status === "monitoring" &&
                    "bg-blue-600/20 text-blue-400",
                  video.status === "declined" &&
                    "bg-gray-600/20 text-gray-400"
                )}
              >
                {video.status === "featured" && "🔥 已上榜"}
                {video.status === "monitoring" && "📊 监控中"}
                {video.status === "declined" && "📉 已衰退"}
              </span>
              <span className="text-dark-textMuted">赛道: {video.channel}</span>
            </div>

            <button
              onClick={handleJudge}
              disabled={judgeMutation.isPending}
              className="btn-primary"
            >
              {judgeMutation.isPending ? "判定中..." : "重新判定"}
            </button>
          </div>

          {judgeMutation.data && (
            <div className="mt-4 p-4 bg-dark-bg rounded-lg">
              <p className="text-white">
                判定结果:{" "}
                <span
                  className={clsx(
                    "font-bold",
                    judgeMutation.data.is_hot
                      ? "text-emerald-400"
                      : "text-gray-400"
                  )}
                >
                  {judgeMutation.data.is_hot ? "🔥 爆款" : "普通视频"}
                </span>
              </p>
              <p className="text-dark-textMuted text-sm mt-1">
                {judgeMutation.data.reason}
              </p>
            </div>
          )}
        </div>

        {/* Trend Chart */}
        <div className="card p-6">
          <h2 className="text-lg font-bold text-white mb-4">播放趋势</h2>
          <TrendChart data={trendData} labels={trendLabels} />
        </div>

        {/* AI Analysis Section */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-yellow-400" />
              AI分析
            </h2>
          </div>

          {aiAnalysis ? (
            <div className="space-y-4">
              {/* Cover Analysis */}
              {aiAnalysis.cover_analysis && (
                <div className="bg-dark-bg rounded-lg p-4">
                  <h3 className="text-sm font-medium text-yellow-400 mb-3">封面分析</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                    <div>
                      <span className="text-dark-textMuted">构图:</span>
                      <span className="text-white ml-1">{aiAnalysis.cover_analysis.cover_composition || '-'}</span>
                    </div>
                    <div>
                      <span className="text-dark-textMuted">色彩:</span>
                      <span className="text-white ml-1">{aiAnalysis.cover_analysis.cover_color_scheme || '-'}</span>
                    </div>
                    <div>
                      <span className="text-dark-textMuted">风格:</span>
                      <span className="text-white ml-1">{aiAnalysis.cover_analysis.cover_visual_style || '-'}</span>
                    </div>
                    <div>
                      <span className="text-dark-textMuted">氛围:</span>
                      <span className="text-white ml-1">{aiAnalysis.cover_analysis.cover_mood_atmosphere || '-'}</span>
                    </div>
                  </div>
                  {aiAnalysis.cover_analysis.cover_visual_highlights?.length > 0 && (
                    <div className="mt-2">
                      <span className="text-dark-textMuted text-sm">视觉亮点:</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {aiAnalysis.cover_analysis.cover_visual_highlights.map((highlight: string, idx: number) => (
                          <span key={idx} className="px-2 py-0.5 bg-yellow-500/20 text-yellow-400 rounded text-xs">
                            {highlight}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Content Analysis */}
              {aiAnalysis.content_analysis && (
                <div className="bg-dark-bg rounded-lg p-4">
                  <h3 className="text-sm font-medium text-blue-400 mb-3">内容分析</h3>
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="text-dark-textMuted">选题:</span>
                      <span className="text-white ml-1">{aiAnalysis.content_analysis.topic_summary || '-'}</span>
                    </div>
                    {aiAnalysis.content_analysis.viral_logic_analysis && (
                      <div className="mt-3">
                        <span className="text-dark-textMuted text-sm">爆款逻辑分析:</span>
                        <p className="text-white mt-1 whitespace-pre-wrap">{aiAnalysis.content_analysis.viral_logic_analysis}</p>
                      </div>
                    )}
                    <div>
                      <span className="text-dark-textMuted">优化建议:</span>
                      <span className="text-white ml-1">{aiAnalysis.content_analysis.content_optimization_suggestions || '-'}</span>
                    </div>
                    <div>
                      <span className="text-dark-textMuted">可复制性:</span>
                      <span className="text-white ml-1">{aiAnalysis.content_analysis.replicability_evaluation || '-'}</span>
                    </div>
                  </div>
                </div>
              )}

              {!aiAnalysis.cover_analysis && !aiAnalysis.content_analysis && (
                <p className="text-dark-textMuted text-center py-4">暂无AI分析结果</p>
              )}
            </div>
          ) : (
            <p className="text-dark-textMuted text-center py-4">暂无AI分析结果</p>
          )}
        </div>
      </div>
    </>
  );
}
