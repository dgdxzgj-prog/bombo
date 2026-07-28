"use client";

import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2, Users, Search, User } from "lucide-react";

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
  const [userStatus, setUserStatus] = useState<{is_login: boolean; user_level: string; username?: string; avatar?: string} | null>(null);
  const [selectedChannel, setSelectedChannel] = useState<string>("");
  const [channels, setChannels] = useState<Channel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const router = useRouter();
  const listRef = useRef<HTMLDivElement>(null);
  const scrollPositionRef = useRef<number>(0);
  const isBfcacheRestoreRef = useRef(false);

  // 恢复滚动位置和赛道选择
  useEffect(() => {
    // 恢复赛道选择（React 状态需要恢复）
    const savedChannel = sessionStorage.getItem("videoListSelectedChannel");
    if (savedChannel) {
      setSelectedChannel(savedChannel);
    }

    // 恢复滚动位置
    const savedPosition = sessionStorage.getItem("videoListScrollPosition");
    if (savedPosition) {
      // 延迟恢复，确保 React 渲染完成
      requestAnimationFrame(() => {
        window.scrollTo(0, parseInt(savedPosition, 10));
      });
    }
  }, []);

  // 记录滚动位置
  const handleScroll = useCallback(() => {
    scrollPositionRef.current = window.scrollY;
  }, []);

  useEffect(() => {
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => {
      sessionStorage.setItem("videoListScrollPosition", scrollPositionRef.current.toString());
      sessionStorage.setItem("videoListSelectedChannel", selectedChannel);
      window.removeEventListener("scroll", handleScroll);
    };
  }, [handleScroll, selectedChannel]);

  const fetchData = async (channel?: string) => {
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
        setUserStatus({
          is_login: statusData.is_login,
          user_level: statusData.user_level,
          username: statusData.username,
          avatar: statusData.avatar,
        });
      }

      // Fetch videos
      const url = channel
        ? `/api/videos/featured?channel=${channel}&limit=20`
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
      const nextOffset = page * 20;
      const url = selectedChannel
        ? `/api/videos/featured?channel=${selectedChannel}&limit=20&offset=${nextOffset}`
        : `/api/videos/featured?limit=20&offset=${nextOffset}`;
      const videosRes = await fetch(url);
      if (videosRes.ok) {
        const videosData = await videosRes.json();
        const newVideos = videosData.videos || [];
        setVideos((prev) => {
          const totalAfterLoad = prev.length + newVideos.length;
          // 还有更多数据且未达到显示上限
          const canLoadMore = newVideos.length === 20 && totalAfterLoad < displayLimit;
          setHasMore(canLoadMore);
          return [...prev, ...newVideos];
        });
        setPage(nextPage);
      }
    } catch (err) {
      console.error("Failed to load more:", err);
    } finally {
      setIsLoadingMore(false);
    }
  };

  // Fetch videos when channel changes
  useEffect(() => {
    fetchData(selectedChannel || "");
  }, [selectedChannel]);

  // Initial data fetch
  useEffect(() => {
    fetchChannels();
  }, []);

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
    <div className="bg-[#f4f5f7] min-h-screen">
      {/* Top Header */}
      <header className="bg-violet-600 text-white safe-area-top">
        <div className="max-w-lg mx-auto">
          {/* Top Row */}
          <div className="flex items-center justify-between px-3 py-2">
            {/* Logo */}
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold tracking-tight">BOMBO</span>
              <span className="text-xs bg-violet-500 px-1.5 py-0.5 rounded">爆款雷达</span>
            </div>

            {/* Search Bar */}
            <Link href="/m/search" className="flex items-center bg-violet-500 hover:bg-violet-400 rounded-full px-3 py-1.5 text-sm text-violet-100 transition-colors mx-2 flex-1 max-w-[180px]">
              <Search className="w-3.5 h-3.5 mr-1.5" />
              <span className="truncate">搜索...</span>
            </Link>

            {/* Right Actions */}
            <div className="flex items-center gap-2">
              {userStatus?.is_login ? (
                <Link href="/m/profile" className="flex items-center gap-1.5">
                  <div className="w-7 h-7 rounded-full bg-violet-400 flex items-center justify-center text-sm font-medium overflow-hidden">
                    {userStatus.avatar ? (
                      <img src={userStatus.avatar} alt="avatar" className="w-full h-full object-cover" />
                    ) : (
                      (userStatus.username?.[0] || "U").toUpperCase()
                    )}
                  </div>
                </Link>
              ) : (
                <button
                  onClick={() => router.push("/login")}
                  className="w-8 h-8 rounded-full bg-violet-500 hover:bg-violet-400 text-white text-xs font-medium transition-colors flex items-center justify-center"
                >
                  登录
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Channel Tags */}
      <div className="px-2 py-1">
        <div className="mb-1">
          <div className="flex gap-1 overflow-x-auto pb-1 scrollbar-hide">
            <button
              onClick={() => setSelectedChannel("")}
              className={`flex-shrink-0 px-2 py-0.5 rounded-full text-xs font-medium transition-colors ${
                selectedChannel === ""
                  ? "bg-violet-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              全部
            </button>
            {channels.map((channel) => (
              <button
                key={channel.channel_id}
                onClick={() => setSelectedChannel(channel.channel_name)}
                className={`flex-shrink-0 px-2 py-0.5 rounded-full text-xs font-medium transition-colors ${
                  selectedChannel === channel.channel_name
                    ? "bg-violet-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {channel.channel_name}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Video List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-violet-600 animate-spin" />
        </div>
      ) : uniqueVideos.length === 0 ? (
        <div className="text-center py-20">
          <p className="text-gray-400">暂无视频数据</p>
        </div>
      ) : (
        <div className="space-y-2 px-2">
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

      {/* Login Modal */}
      {showLoginModal && (
        <LoginModal
          onClose={() => setShowLoginModal(false)}
          onLoginSuccess={() => {
            setShowLoginModal(false);
            // Refresh user status
            const token = localStorage.getItem("bombo_token");
            if (token) {
              fetch("/api/videos/user-status", { headers: { Authorization: `Bearer ${token}` } })
                .then(res => res.json())
                .then(data => {
                  setUserStatus({
                    is_login: data.is_login,
                    user_level: data.user_level,
                    username: data.username,
                    avatar: data.avatar,
                  });
                });
            }
          }}
        />
      )}
    </div>
  );
}

function LoginModal({
  onClose,
  onLoginSuccess,
}: {
  onClose: () => void;
  onLoginSuccess: () => void;
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      const data = await res.json();

      if (res.ok && data.token) {
        localStorage.setItem("bombo_token", data.token);
        onLoginSuccess();
      } else {
        setError(data.message || "登录失败");
      }
    } catch (err) {
      setError("网络错误，请重试");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-[100] flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-xl w-full max-w-sm overflow-hidden" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="bg-blue-600 text-white px-4 py-3 flex items-center justify-between">
          <span className="font-medium">登录 Bombo 账号</span>
          <button onClick={onClose} className="text-blue-200 hover:text-white">✕</button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {error && (
            <div className="bg-red-50 text-red-600 text-sm px-3 py-2 rounded-lg">{error}</div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">用户名</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="请输入用户名"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="请输入密码"
              required
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full bg-blue-600 text-white py-2.5 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? "登录中..." : "登录"}
          </button>

          <div className="text-center text-sm text-gray-500">
            还没有账号？{" "}
            <Link href="/m/pricing" className="text-blue-600 hover:underline" onClick={onClose}>
              立即注册
            </Link>
          </div>
        </form>
      </div>
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
      className={`bg-white rounded-lg shadow-sm overflow-hidden flex relative ${(video.view_yesterday && video.view_today > video.view_yesterday * 1.3) ? "border-2 border-orange-400" : ""}`}
    >
      {/* Cover Image - Left Side - Click to Bilibili */}
      <div
        className="relative w-28 h-20 flex-shrink-0 bg-gray-100 cursor-pointer"
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
            {video.online_count >= 10000
                ? (video.online_count / 10000).toFixed(1) + "万+"
                : video.online_count >= 1000
                ? video.online_count + "+"
                : video.online_count}
          </div>
        )}
        {/* Duration Badge */}
        <div className="absolute bottom-0.5 right-0.5 px-1 py-0.5 rounded bg-black/70 text-white text-[10px] font-medium">
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
      <div className="flex-1 p-2 flex flex-col justify-between cursor-pointer" onClick={handleCardClick}>
        <div>
          <h3 className="text-sm font-medium text-gray-800 line-clamp-2 leading-tight">
            {video.title}
          </h3>
        </div>
        <div className="flex items-center justify-between mt-0.5">
          <span className="text-xs text-gray-500 truncate max-w-[80px]">{video.author}</span>
        </div>
        <div className="flex items-center gap-1 mt-1 text-xs text-gray-400">
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
          <span className="text-gray-400">
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
          <span className={video.view_today > 0 && ((video.like_count || 0) + (video.favorite_count || 0) + (video.reply_count || 0) + (video.coin_count || 0) + (video.share_count || 0)) / video.view_today * 100 > 18 ? "px-1 py-0.5 border border-purple-400 text-purple-400 rounded" : "text-gray-400"}>
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
