"use client";

import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { Loader2, Users } from "lucide-react";

interface Video {
  bvid: string;
  title: string;
  author: string;
  channel: string;
  cover_url?: string;
  view_today: number;
  view_yesterday?: number;
  growth_rate: number;
  like_count?: number;
  favorite_count?: number;
  reply_count?: number;
  coin_count?: number;
  share_count?: number;
  online_count?: number;
  status: string;
  pubdate?: string;
  author_fans?: number;
  duration?: number;
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

export default function MobileHomePage() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [userStatus, setUserStatus] = useState<UserStatus | null>(null);
  const [selectedChannel, setSelectedChannel] = useState<string>("");
  const [channels, setChannels] = useState<Channel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const router = useRouter();
  const listRef = useRef<HTMLDivElement>(null);
  const scrollPositionRef = useRef<number>(0);

  // 恢复滚动位置
  useEffect(() => {
    const savedPosition = sessionStorage.getItem("videoListScrollPosition");
    const savedChannel = sessionStorage.getItem("videoListSelectedChannel");

    if (savedChannel) {
      setSelectedChannel(savedChannel);
    }

    if (savedPosition && savedChannel === selectedChannel) {
      setTimeout(() => {
        window.scrollTo(0, parseInt(savedPosition, 10));
      }, 100);
    }
  }, []);

  // Fetch channels on mount
  useEffect(() => {
    fetchChannels();
  }, []);

  useEffect(() => {
    fetchData();
  }, [selectedChannel]);

  // 记录滚动位置
  const handleScroll = useCallback(() => {
    scrollPositionRef.current = window.scrollY;
  }, []);

  useEffect(() => {
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => {
      // 保存滚动位置到 sessionStorage
      sessionStorage.setItem("videoListScrollPosition", scrollPositionRef.current.toString());
      sessionStorage.setItem("videoListSelectedChannel", selectedChannel);
      window.removeEventListener("scroll", handleScroll);
    };
  }, [handleScroll, selectedChannel]);

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

  const fetchChannels = async () => {
    try {
      const res = await fetch("/api/channels/active");
      if (res.ok) {
        const data = await res.json();
        setChannels(data.channels || []);
      }
    } catch (err) {
      console.error("Failed to fetch channels:", err);
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

  const formatViews = (views: number) => {
    if (views >= 100000000) return (views / 100000000).toFixed(1) + "亿";
    if (views >= 10000) return (views / 10000).toFixed(1) + "w";
    return views.toString();
  };

  const getVideoListLimit = () => {
    // tourist: 40, free/light/standard/pro: unlimited (handled by backend)
    if (userStatus?.user_level === "tourist") return 40;
    return Infinity;
  };

  // Deduplicate videos by bvid to avoid duplicate key warnings
  const uniqueVideos = useMemo(() => {
    const seen = new Set<string>();
    return videos.filter((video) => {
      if (seen.has(video.bvid)) return false;
      seen.add(video.bvid);
      return true;
    });
  }, [videos]);

  const displayLimit = userStatus?.user_level === "tourist" ? 40 : Infinity;

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
          {channels.map((channel) => (
            <button
              key={channel.channel_id}
              onClick={() => setSelectedChannel(channel.channel_name)}
              className={`flex-shrink-0 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                selectedChannel === channel.channel_name
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {channel.channel_name}
            </button>
          ))}
        </div>
      </div>

      {/* Video List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
        </div>
      ) : uniqueVideos.length === 0 ? (
        <div className="text-center py-20">
          <p className="text-gray-400">暂无视频数据</p>
        </div>
      ) : (
        <div className="space-y-4">
          {uniqueVideos.slice(0, displayLimit).map((video) => (
            <VideoCard
              key={video.bvid}
              video={video}
              formatViews={formatViews}
            />
          ))}

          {hasMore && uniqueVideos.length < displayLimit && (
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
  formatViews: (views: number) => string;
}

function VideoCard({ video, formatViews }: VideoCardProps) {
  const router = useRouter();

  const handleCardClick = () => {
    router.push(`/m/video/${video.bvid}`);
  };

  const handleJumpToBilibili = (e: React.MouseEvent) => {
    e.stopPropagation();
    window.open(`https://www.bilibili.com/video/${video.bvid}`, "_blank");
  };

  // 使用后端代理获取封面图片，解决B站防盗链403问题
  // 确保使用https协议
  const secureCoverUrl = video.cover_url?.replace(/^http:\/\//i, "https://");
  const coverProxyUrl = secureCoverUrl
    ? `/api/videos/cover-proxy?url=${encodeURIComponent(secureCoverUrl)}`
    : null;

  return (
    <div
      className={`bg-white rounded-xl shadow-sm overflow-hidden flex relative ${(video.view_yesterday && video.view_today > video.view_yesterday * 1.3) ? "border-2 border-orange-400" : ""}`}
    >
      {/* Cover Image - Left Side - Click to Bilibili */}
      <div
        className="relative w-36 h-24 flex-shrink-0 bg-gray-100 cursor-pointer"
        onClick={handleJumpToBilibili}
      >
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
              video.online_count >= 10000
                ? "bg-purple-50 border-purple-400 text-purple-600"
                : video.online_count >= 5000
                ? "bg-pink-50 border-pink-400 text-pink-600"
                : video.online_count >= 1000
                ? "bg-orange-50 border-orange-400 text-orange-600"
                : "bg-yellow-50 border-yellow-400 text-yellow-600"
            }`}
          >
            <Users className="w-2.5 h-2.5" />
            {video.online_count >= 10000 ? (video.online_count / 10000).toFixed(1) + "万" : video.online_count}
          </div>
        )}
        {/* Duration Badge */}
        <div className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/70 text-white text-xs font-medium">
          {(() => {
            const duration = video.duration || 0;
            const h = Math.floor(duration / 3600);
            const m = Math.floor((duration % 3600) / 60);
            const s = duration % 60;
            if (h > 0) return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
            return `${m}:${s.toString().padStart(2, "0")}`;
          })()}
        </div>
      </div>

      {/* Video Info - Right Side - Click to Detail */}
      <div className="flex-1 p-2.5 flex flex-col justify-between cursor-pointer" onClick={handleCardClick}>
        <div>
          <h3 className="text-sm font-medium text-gray-800 line-clamp-2 leading-tight">
            {video.title}
          </h3>
        </div>
        <div className="flex items-center justify-between mt-1">
          <span className="text-xs text-gray-500 truncate max-w-[80px]">{video.author}</span>
        </div>
        <div className="flex items-center gap-1 mt-1.5 text-xs text-gray-500">
          <span className={
            video.view_today >= 10000000
              ? "px-1 py-0.5 border border-purple-400 text-purple-500 rounded"
              : (video.view_today >= 1200000 && video.pubdate && (Date.now() - new Date(video.pubdate).getTime()) < 72 * 60 * 60 * 1000) ||
                (video.view_today >= 3000000 && video.pubdate && (Date.now() - new Date(video.pubdate).getTime()) >= 72 * 60 * 60 * 1000 && (Date.now() - new Date(video.pubdate).getTime()) < 168 * 60 * 60 * 1000)
              ? "px-1 py-0.5 border border-orange-400 text-orange-500 rounded"
              : ""
          }>
            {video.view_today >= 10000 ? formatViews(video.view_today) + "播放" : formatViews(video.view_today)}
          </span>
          <span>·</span>
          <span>
            {video.pubdate ? (
              (() => {
                const diff = Date.now() - new Date(video.pubdate).getTime();
                const hours = Math.floor(diff / (1000 * 60 * 60));
                const days = Math.floor(hours / 24);
                if (hours < 1) return '刚刚';
                if (hours < 24) return `${hours}小时前`;
                if (days < 30) return `${days}天前`;
                return new Date(video.pubdate).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
              })()
            ) : '未知'}
          </span>
          <span>·</span>
          <span className={video.view_today > 0 && ((video.like_count || 0) + (video.favorite_count || 0) + (video.reply_count || 0) + (video.coin_count || 0) + (video.share_count || 0)) / video.view_today * 100 > 18 ? "px-1 py-0.5 border border-purple-400 text-purple-500 rounded" : ""}>
            {video.view_today > 0 ? (
              (() => {
                const interaction = (video.like_count || 0) + (video.favorite_count || 0) + (video.reply_count || 0) + (video.coin_count || 0) + (video.share_count || 0);
                const rate = ((interaction / video.view_today) * 100).toFixed(1);
                return `${rate}%互动`
              })()
            ) : '0%互动'}
          </span>
        </div>
      </div>
    </div>
  );
}
