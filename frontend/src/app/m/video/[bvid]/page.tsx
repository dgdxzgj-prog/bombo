"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Loader2, Users, MessageCircle } from "lucide-react";

interface Video {
  bvid: string;
  title: string;
  author: string;
  channel: string;
  cover_url?: string;
  view_today: number;
  view_yesterday?: number;
  growth_rate: number;
  online_count?: number;
  like_count: number;
  favorite_count: number;
  reply_count: number;
  pubdate?: string;
  status: string;
  ai_analysis?: {
    cover_analysis?: {
      cover_composition?: string;
      cover_main_element?: string;
      cover_color_scheme?: string;
      cover_visual_style?: string;
      cover_mood_atmosphere?: string;
      cover_audience_expectation?: string;
    };
    content_analysis?: {
      topic_summary?: string;
      viral_logic_analysis?: string;
      content_optimization_suggestions?: string;
      replicability_evaluation?: string;
    };
  };
}

export default function MobileVideoPage() {
  const params = useParams();
  const router = useRouter();
  const bvid = params.bvid as string;

  const [video, setVideo] = useState<Video | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchVideoDetail();
  }, [bvid]);

  const fetchVideoDetail = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`/api/videos/${bvid}`);
      if (res.ok) {
        const data = await res.json();
        setVideo(data);
      }
    } catch (err) {
      console.error("Failed to fetch video:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const formatViews = (views: number) => {
    if (views >= 100000000) return (views / 100000000).toFixed(1) + "亿";
    if (views >= 10000) return (views / 10000).toFixed(1) + "万";
    return views.toString();
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
      </div>
    );
  }

  if (!video) {
    return (
      <div className="text-center py-20">
        <p className="text-gray-400">视频不存在</p>
      </div>
    );
  }

  // 使用后端代理获取封面图片，确保使用https协议
  const secureCoverUrl = video.cover_url?.replace(/^http:\/\//i, "https://");
  const coverProxyUrl = secureCoverUrl
    ? `/api/videos/cover-proxy?url=${encodeURIComponent(secureCoverUrl)}`
    : null;

  return (
    <div className="pb-4">
      {/* Header */}
      <div className="sticky top-0 bg-white border-b border-gray-100 z-10 px-3 py-2 flex items-center gap-3">
        <button
          onClick={() => router.back()}
          className="p-1.5 -ml-1.5 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-gray-600" />
        </button>
        <span className="font-medium text-gray-800 text-sm truncate flex-1">
          视频详情
        </span>

      </div>

      {/* Video Info */}
      <div className="px-3 py-3">
        {/* Cover */}
        <div className="relative aspect-video bg-gray-100 rounded-xl overflow-hidden mb-3">
          {coverProxyUrl && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={coverProxyUrl} alt={video.title} className="w-full h-full object-cover" />
          )}
          {video.online_count && video.online_count > 0 && (
            <div
              className={`absolute bottom-2 right-2 px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1 border ${
                video.online_count > 10000
                  ? "bg-red-50 border-red-400 text-red-600"
                  : video.online_count > 1000
                  ? "bg-orange-50 border-orange-400 text-orange-600"
                  : "bg-yellow-50 border-yellow-400 text-yellow-600"
              }`}
            >
              <Users className="w-3 h-3" />
              {video.online_count >= 10000 ? (video.online_count / 10000).toFixed(1) + "万" : video.online_count}
            </div>
          )}
        </div>

        {/* Title & Meta */}
        <h1 className="text-base font-bold text-gray-800 mb-2">{video.title}</h1>
        <div className="flex items-center gap-3 text-xs text-gray-500 mb-3">
          <span>{video.author}</span>
          <span>·</span>
          <span>{video.channel}</span>
          <span>·</span>
          <span>{video.pubdate ? new Date(video.pubdate).toLocaleString('zh-CN') : '未知'}</span>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-2 mb-4">
          <div className="bg-gray-50 rounded-lg p-2.5 text-center">
            <p className="text-sm font-bold text-gray-800">{formatViews(video.view_today)}</p>
            <p className="text-xs text-gray-500">播放</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-2.5 text-center">
            <p className="text-sm font-bold text-gray-800">{formatViews(video.like_count)}</p>
            <p className="text-xs text-gray-500">点赞</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-2.5 text-center">
            <p className="text-sm font-bold text-gray-800">{formatViews(video.favorite_count)}</p>
            <p className="text-xs text-gray-500">收藏</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-2.5 text-center">
            <p className="text-sm font-bold text-gray-800">{formatViews(video.reply_count)}</p>
            <p className="text-xs text-gray-500 flex items-center justify-center gap-1"><MessageCircle className="w-3 h-3" />评论</p>
          </div>
        </div>

        {/* AI Analysis */}
        {video.ai_analysis && (
          <div className="space-y-3">
            <h2 className="font-medium text-gray-800">AI分析结果</h2>

            {video.ai_analysis.cover_analysis && (
              <div className="bg-white rounded-xl p-3 shadow-sm">
                <h3 className="text-sm font-medium text-gray-700 mb-2">封面分析</h3>
                <div className="space-y-1.5 text-xs text-gray-600">
                  <p><span className="text-gray-400">主体元素：</span>{video.ai_analysis.cover_analysis.cover_main_element}</p>
                  <p><span className="text-gray-400">配色方案：</span>{video.ai_analysis.cover_analysis.cover_color_scheme}</p>
                  <p><span className="text-gray-400">视觉风格：</span>{video.ai_analysis.cover_analysis.cover_visual_style}</p>
                  <p><span className="text-gray-400">情绪氛围：</span>{video.ai_analysis.cover_analysis.cover_mood_atmosphere}</p>
                  <p><span className="text-gray-400">观众期待：</span>{video.ai_analysis.cover_analysis.cover_audience_expectation}</p>
                </div>
              </div>
            )}

            {video.ai_analysis.content_analysis && (
              <div className="bg-white rounded-xl p-3 shadow-sm">
                <h3 className="text-sm font-medium text-gray-700 mb-2">内容分析</h3>
                <div className="space-y-1.5 text-xs text-gray-600">
                  <p><span className="text-gray-400">话题总结：</span>{video.ai_analysis.content_analysis.topic_summary}</p>
                  {video.ai_analysis.content_analysis.viral_logic_analysis && (
                    <p><span className="text-gray-400">爆款逻辑：</span>{video.ai_analysis.content_analysis.viral_logic_analysis}</p>
                  )}
                  {video.ai_analysis.content_analysis.content_optimization_suggestions && (
                    <p><span className="text-gray-400">优化建议：</span>{video.ai_analysis.content_analysis.content_optimization_suggestions}</p>
                  )}
                  {video.ai_analysis.content_analysis.replicability_evaluation && (
                    <p><span className="text-gray-400">可复制性：</span>{video.ai_analysis.content_analysis.replicability_evaluation}</p>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {!video.ai_analysis && (
          <div className="bg-gray-50 rounded-xl p-4 text-center">
            <p className="text-gray-500 text-sm">暂无AI分析结果</p>
            <p className="text-gray-400 text-xs mt-1">点击"AI分析"按钮生成分析报告</p>
          </div>
        )}
      </div>
    </div>
  );
}
