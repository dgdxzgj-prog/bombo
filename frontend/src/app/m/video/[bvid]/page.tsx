"use client";

import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2, Users, MessageCircle, Eye, Heart, Star, Hash, User, Folder, ChevronLeft } from "lucide-react";

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
  coin_count: number;
  share_count: number;
  reply_count: number;
  pubdate?: string;
  status: string;
  duration?: number;
  tags?: string[];
  author_avatar?: string;
  author_fans?: number;
  author_video_count?: number;
  ai_analysis?: {
    bvid: string;
    created_at?: string;
    cover_analysis?: {
      composition?: {
        rule?: string;
        description?: string;
      };
      elements?: {
        subjects?: string;
        text?: string;
        color_palette?: string;
        lighting?: string;
      };
      style?: {
        overall?: string;
        mood?: string;
      };
      appeal?: {
        attraction?: string;
        hook?: string;
      };
    };
    content_analysis?: {
      shortTopic?: string;
      summaryInsight?: string;
      optimizationSuggestions?: string;
    };
  };
}

export default function MobileVideoPage() {
  const params = useParams();
  const router = useRouter();
  const bvid = params.bvid as string;

  const [video, setVideo] = useState<Video | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [swipeHint, setSwipeHint] = useState(false);

  // 右滑返回手势
  const touchStartX = useRef<number>(0);
  const touchEndX = useRef<number>(0);

  useEffect(() => {
    // 显示滑动提示
    const hasSwipedBefore = sessionStorage.getItem("hasSwipedBack");
    if (!hasSwipedBefore) {
      setSwipeHint(true);
      setTimeout(() => setSwipeHint(false), 3000);
    }
  }, []);

  useEffect(() => {
    fetchVideoDetail();
  }, [bvid]);

  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX;
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    touchEndX.current = e.touches[0].clientX;
  };

  const handleTouchEnd = () => {
    const diff = touchEndX.current - touchStartX.current;
    // 右滑超过100px且在左侧边缘触发
    if (diff > 100 && touchStartX.current < 50) {
      window.history.back();
    }
  };

  const handleBack = () => {
    window.history.back();
  };

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

  const formatDuration = (seconds: number) => {
    if (!seconds) return "";
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
    return `${m}:${s.toString().padStart(2, "0")}`;
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
    <div
      className="pb-4"
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {/* Swipe Hint Toast */}
      {swipeHint && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 bg-gray-800/90 text-white text-xs px-4 py-2 rounded-full z-50 animate-fade-in-out">
          ← 左滑边缘可返回榜单
        </div>
      )}

      {/* Video Info */}
      <div className="px-3 py-3">
        {/* Cover - Top Full Width 16:9 */}
        <a
          href={`https://www.bilibili.com/video/${video.bvid}`}
          target="_blank"
          rel="noopener noreferrer"
          className="block relative w-full aspect-video bg-gray-100 rounded-md overflow-hidden mb-3"
        >
          {coverProxyUrl && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={coverProxyUrl} alt={video.title} className="w-full h-full object-cover" />
          )}
          {video.online_count && video.online_count > 0 && (
            <div
              className={`absolute top-2 left-2 px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1 border ${
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
          {video.duration && video.duration > 0 && (
            <div className="absolute bottom-2 right-2 px-1.5 py-0.5 rounded bg-black/70 text-white text-xs font-medium">
              {formatDuration(video.duration)}
            </div>
          )}
        </a>

        {/* Title Below Cover */}
        <h1 className="text-base font-bold text-gray-800 mb-2">{video.title}</h1>

        {/* Author & Stats Row */}
        <div className="flex items-center justify-between gap-3 text-xs text-gray-500 mb-2">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <User className="w-3 h-3" />{video.author}
            </span>
            <span>|</span>
            <span className="px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
              {video.channel}
            </span>
          </div>
          <span className="text-gray-400">
            {video.pubdate ? new Date(video.pubdate).toLocaleString('zh-CN') : '未知'}
          </span>
        </div>

        {/* Stats Row */}
        <div className="flex items-center gap-4 text-xs mb-3">
          <span className="flex items-center gap-1 text-gray-600">
            <Eye className="w-3 h-3" />{formatViews(video.view_today)}
          </span>
          <span className="flex items-center gap-1 text-gray-600">
            <Heart className="w-3 h-3" />{formatViews(video.like_count)}
          </span>
          <span className="flex items-center gap-1 text-gray-600">
            <Star className="w-3 h-3" />{formatViews(video.favorite_count)}
          </span>
          <span className="flex items-center gap-1 text-gray-600">
            <MessageCircle className="w-3 h-3" />{formatViews(video.reply_count)}
          </span>
          </div>

        {/* Tags */}
        {video.tags && video.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {video.tags.map((tag, index) => (
              <span
                key={index}
                className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-full"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* AI Analysis */}
        {video.ai_analysis && video.ai_analysis.content_analysis && (
          <div className="space-y-3">
            {video.ai_analysis.content_analysis.shortTopic && (
              <div className="bg-white rounded-xl p-3 shadow-sm">
                <p className="text-xs text-gray-600"><span className="text-gray-700 font-medium">选题：</span>{video.ai_analysis.content_analysis.shortTopic}</p>
              </div>
            )}

            {video.ai_analysis.content_analysis.summaryInsight && (
              <div className="bg-white rounded-xl p-3 shadow-sm">
                <h3 className="text-sm font-medium text-gray-700 mb-2">爆款分析</h3>
                <p className="text-xs text-gray-600 whitespace-pre-wrap">{video.ai_analysis.content_analysis.summaryInsight}</p>
              </div>
            )}

            {video.ai_analysis && video.ai_analysis.cover_analysis && (
              <div className="bg-white rounded-xl p-3 shadow-sm">
                <h3 className="text-sm font-medium text-gray-700 mb-2">封面分析</h3>
                <div className="space-y-1.5 text-xs text-gray-600">
                  {video.ai_analysis.cover_analysis.elements?.subjects && (
                    <p><span className="text-gray-400">主体元素：</span>{video.ai_analysis.cover_analysis.elements.subjects}</p>
                  )}
                  {video.ai_analysis.cover_analysis.elements?.color_palette && (
                    <p><span className="text-gray-400">配色方案：</span>{video.ai_analysis.cover_analysis.elements.color_palette}</p>
                  )}
                  {video.ai_analysis.cover_analysis.style?.overall && (
                    <p><span className="text-gray-400">视觉风格：</span>{video.ai_analysis.cover_analysis.style.overall}</p>
                  )}
                  {video.ai_analysis.cover_analysis.style?.mood && (
                    <p><span className="text-gray-400">情绪氛围：</span>{video.ai_analysis.cover_analysis.style.mood}</p>
                  )}
                  {video.ai_analysis.cover_analysis.appeal?.hook && (
                    <p><span className="text-gray-400">观众期待：</span>{video.ai_analysis.cover_analysis.appeal.hook}</p>
                  )}
                </div>
              </div>
            )}

            {video.ai_analysis.content_analysis.optimizationSuggestions && (
              <div className="bg-white rounded-xl p-3 shadow-sm">
                <h3 className="text-sm font-medium text-gray-700 mb-2">优化建议</h3>
                <p className="text-xs text-gray-600">{video.ai_analysis.content_analysis.optimizationSuggestions}</p>
              </div>
            )}

            {!video.ai_analysis.content_analysis.shortTopic &&
             !video.ai_analysis.content_analysis.summaryInsight &&
             !video.ai_analysis.content_analysis.optimizationSuggestions && (
              <div className="bg-gray-50 rounded-xl p-3 text-center">
                <p className="text-gray-500 text-xs">暂无选题分析内容</p>
              </div>
            )}
          </div>
        )}

        {!video.ai_analysis && (
          <div className="bg-gray-50 rounded-xl p-4 text-center">
            <p className="text-gray-500 text-sm">暂无AI分析结果</p>
            <p className="text-gray-400 text-xs mt-1">点击&quotAI分析&quot按钮生成分析报告</p>
          </div>
        )}
      </div>
    </div>
  );
}
