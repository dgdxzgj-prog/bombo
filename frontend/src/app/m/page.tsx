"use client";

import { useEffect, useState, useCallback } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { ExternalLink, Loader2, Users } from "lucide-react";

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
  status: string;
}

interface UserStatus {
  user_level: string;
  is_login: boolean;
  permissions: {
    user_level: string;
    is_paid: boolean;
    tier: string | null;
    status_label: string;
    trial_count?: number;
    upgrade_hint?: string;
  };
  quotas: {
    day_self_analysis?: { remaining: number; total: number };
  };
}

interface Channel {
  channel_id: string;
  channel_name: string;
}

const CHANNEL_LIST = ["美食", "数码", "游戏", "知识", "短剧", "生活", "科技", "汽车"];

export default function MobileHomePage() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [userStatus, setUserStatus] = useState<UserStatus | null>(null);
  const [selectedChannel, setSelectedChannel] = useState<string>("");
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const router = useRouter();

  useEffect(() => {
    fetchData();
  }, [selectedChannel]);

  const fetchData = async () => {
    setIsLoading(true);
    setPage(1);
    try {
      // Fetch user status (with auth token if available)
      const token = localStorage.getItem("bombo_token");
      const headers: HeadersInit = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      const statusRes = await fetch("/api/videos/user-status", { headers });
      if (statusRes.ok) {
        const statusData = await statusRes.json();
        setUserStatus(statusData);
      }

      // Fetch videos
      const url = selectedChannel
        ? `/api/videos/featured?channel=${selectedChannel}&limit=20`
        : `/api/videos/featured?limit=20`;
      const videosRes = await fetch(url);
      if (videosRes.ok) {
        const videosData = await videosRes.json();
        setVideos(videosData.videos || []);
        setHasMore(videosData.videos?.length === 20);
      }
    } catch (err) {
      console.error("Failed to fetch data:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const loadMore = async () => {
    if (isLoadingMore || !hasMore) return;
    setIsLoadingMore(true);
    try {
      const nextPage = page + 1;
      const url = selectedChannel
        ? `/api/videos/featured?channel=${selectedChannel}&limit=20&offset=${nextPage * 20}`
        : `/api/videos/featured?limit=20&offset=${nextPage * 20}`;
      const videosRes = await fetch(url);
      if (videosRes.ok) {
        const videosData = await videosRes.json();
        setVideos((prev) => [...prev, ...(videosData.videos || [])]);
        setHasMore(videosData.videos?.length === 20);
        setPage(nextPage);
      }
    } catch (err) {
      console.error("Failed to load more:", err);
    } finally {
      setIsLoadingMore(false);
    }
  };

  const handleAIFeature = async (bvid: string) => {
    // Check if tourist (not logged in) and has trial remaining
    if (!userStatus?.is_login) {
      if (userStatus?.user_level === "tourist" && (userStatus.permissions?.trial_count || 0) > 0) {
        // Tourist with trial remaining - proceed to use trial
        const trialRes = await fetch("/api/videos/trial-use", { method: "POST" });
        if (trialRes.ok) {
          const trialData = await trialRes.json();
          if (trialData.exhausted) {
            alert("试用次数已用完，请登录或升级会员");
            router.push("/login");
            return;
          }
        }
        router.push(`/m/analysis?bvid=${bvid}`);
        return;
      }
      // Not logged in and not tourist with trial - go to login
      router.push("/login");
      return;
    }

    // Logged in user - navigate to AI analysis
    router.push(`/m/analysis?bvid=${bvid}`);
  };

  const formatViews = (views: number) => {
    if (views >= 100000000) return (views / 100000000).toFixed(1) + "亿";
    if (views >= 10000) return (views / 10000).toFixed(1) + "万";
    return views.toString();
  };

  const getPermissionHint = () => {
    if (!userStatus) return "";
    if (userStatus.user_level === "tourist") {
      return `游客试用剩余${userStatus.permissions.trial_count || 0}次，仅展示前40条`;
    }
    if (userStatus.user_level === "free") {
      return "注册免费浏览全榜单，升级解锁抽帧拆解";
    }
    return "";
  };

  const canUseFrameExtract = () => {
    return ["light", "standard", "pro"].includes(userStatus?.user_level || "");
  };

  const getVideoListLimit = () => {
    // tourist: 40, free/light/standard/pro: unlimited (handled by backend)
    if (userStatus?.user_level === "tourist") return 40;
    return Infinity;
  };

  return (
    <div className="px-3 py-4">
      {/* Channel Tags */}
      <div className="mb-4">
        <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
          <button
            onClick={() => setSelectedChannel("")}
            className={`flex-shrink-0 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
              selectedChannel === ""
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            全部
          </button>
          {CHANNEL_LIST.map((channel) => (
            <button
              key={channel}
              onClick={() => setSelectedChannel(channel)}
              className={`flex-shrink-0 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                selectedChannel === channel
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {channel}
            </button>
          ))}
        </div>
      </div>

      {/* Permission Hint */}
      {getPermissionHint() && (
        <div className="mb-4 px-3 py-2 bg-blue-50 rounded-lg">
          <p className="text-blue-600 text-xs">{getPermissionHint()}</p>
        </div>
      )}

      {/* Video List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
        </div>
      ) : videos.length === 0 ? (
        <div className="text-center py-20">
          <p className="text-gray-400">暂无视频数据</p>
        </div>
      ) : (
        <div className="space-y-4">
          {videos.slice(0, getVideoListLimit()).map((video) => (
            <VideoCard
              key={video.bvid}
              video={video}
              onAIFeature={() => handleAIFeature(video.bvid)}
              canFrameExtract={canUseFrameExtract()}
              formatViews={formatViews}
            />
          ))}

          {hasMore && videos.length < (getVideoListLimit() || Infinity) && (
            <button
              onClick={loadMore}
              disabled={isLoadingMore}
              className="w-full py-3 bg-gray-100 text-gray-600 rounded-lg text-sm font-medium hover:bg-gray-200 disabled:opacity-50"
            >
              {isLoadingMore ? "加载中..." : "加载更多"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

interface VideoCardProps {
  video: Video;
  onAIFeature: () => void;
  canFrameExtract: boolean;
  formatViews: (views: number) => string;
}

function VideoCard({ video, onAIFeature, canFrameExtract, formatViews }: VideoCardProps) {
  const router = useRouter();

  const handleCardClick = () => {
    router.push(`/m/video/${video.bvid}`);
  };

  const handleJumpToBilibili = (e: React.MouseEvent) => {
    e.stopPropagation();
    window.open(`https://www.bilibili.com/video/${video.bvid}`, "_blank");
  };

  const handleAIFeature = (e: React.MouseEvent) => {
    e.stopPropagation();
    onAIFeature();
  };

  // 使用后端代理获取封面图片，解决B站防盗链403问题
  // 确保使用https协议
  const secureCoverUrl = video.cover_url?.replace(/^http:\/\//i, "https://");
  const coverProxyUrl = secureCoverUrl
    ? `/api/videos/cover-proxy?url=${encodeURIComponent(secureCoverUrl)}`
    : null;

  return (
    <div
      className="bg-white rounded-xl shadow-sm overflow-hidden flex cursor-pointer active:bg-gray-50"
      onClick={handleCardClick}
    >
      {/* Cover Image - Left Side */}
      <div className="relative w-36 h-24 flex-shrink-0 bg-gray-100">
        {coverProxyUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={coverProxyUrl}
            alt={video.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400 text-xs">
            暂无封面
          </div>
        )}
        {/* Online Count Badge */}
        {video.online_count && video.online_count > 0 && (
          <div
            className={`absolute bottom-1 left-1 px-1.5 py-0.5 rounded-full text-xs font-medium flex items-center gap-0.5 border ${
              video.online_count > 10000
                ? "bg-red-50 border-red-400 text-red-600"
                : video.online_count > 1000
                ? "bg-orange-50 border-orange-400 text-orange-600"
                : "bg-yellow-50 border-yellow-400 text-yellow-600"
            }`}
          >
            <Users className="w-2.5 h-2.5" />
            {video.online_count >= 10000 ? (video.online_count / 10000).toFixed(1) + "万" : video.online_count}
          </div>
        )}
      </div>

      {/* Video Info - Right Side */}
      <div className="flex-1 p-2.5 flex flex-col justify-between">
        <div>
          <h3 className="text-sm font-medium text-gray-800 line-clamp-2 leading-tight">
            {video.title}
          </h3>
        </div>
        <div className="flex items-center justify-between mt-1">
          <span className="text-xs text-gray-500 truncate max-w-[80px]">{video.author}</span>
          <span className="text-xs text-gray-400">{formatViews(video.view_today)}</span>
        </div>
        <div className="flex gap-1.5 mt-1.5">
          <button
            onClick={handleAIFeature}
            className="flex-1 py-1.5 bg-blue-50 text-blue-600 rounded text-xs font-medium hover:bg-blue-100 transition-colors"
          >
            AI分析
          </button>
          {canFrameExtract && (
            <button className="flex-1 py-1.5 bg-orange-50 text-orange-600 rounded text-xs font-medium hover:bg-orange-100 transition-colors">
              抽帧
            </button>
          )}
          <button
            onClick={handleJumpToBilibili}
            className="py-1.5 px-2 bg-gray-50 text-gray-500 rounded text-xs hover:bg-gray-100 transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
