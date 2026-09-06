"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Plus, X, RefreshCw, Search, Users } from "lucide-react";

interface UserKeyword {
  id: number;
  keyword: string;
  channel: string;
  status: number;
  created_at: string;
  video_count: number;
}

interface FeedVideo {
  bvid: string;
  title: string;
  author: string;
  channel: string;
  keyword: string;
  view_today: number;
  view_yesterday?: number;
  growth_rate: number;
  like_count: number;
  favorite_count: number;
  reply_count: number;
  coin_count?: number;
  share_count?: number;
  online_count: number;
  max_online_today: number;
  cover_url: string;
  status: string;
  featured_at: string;
  first_seen: string;
  pubdate?: string;
  duration?: number;
}

export default function MyFeedPage() {
  const [userStatus, setUserStatus] = useState<{ is_login: boolean; username?: string } | null>(null);
  const [keywords, setKeywords] = useState<UserKeyword[]>([]);
  const [allFeaturedVideos, setAllFeaturedVideos] = useState<FeedVideo[]>([]); // 所有上榜视频，用于计算关键词数量
  const [videos, setVideos] = useState<FeedVideo[]>([]); // 当前显示的视频（已过滤）
  const [isLoading, setIsLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newKeyword, setNewKeyword] = useState("");
  const [isAdding, setIsAdding] = useState(false);

  // Filters
  const [selectedKeyword, setSelectedKeyword] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  const router = useRouter();

  const fetchUserStatus = useCallback(async () => {
    try {
      const token = localStorage.getItem("bombo_token");
      const headers: HeadersInit = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch("/api/videos/user-status", { headers });
      if (res.ok) {
        const data = await res.json();
        setUserStatus({ is_login: data.is_login, username: data.username });
      }
    } catch (err) {
      console.error("Failed to fetch user status:", err);
    }
  }, []);

  const fetchKeywords = useCallback(async () => {
    try {
      const token = localStorage.getItem("bombo_token");
      const res = await fetch("/api/user/keywords", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setKeywords(data.keywords || []);
      }
    } catch (err) {
      console.error("Failed to fetch keywords:", err);
    }
  }, []);

  const fetchVideos = useCallback(async () => {
    try {
      const token = localStorage.getItem("bombo_token");

      // 1. 获取所有上榜视频（用于计算各关键词的上榜数量）
      const allParams = new URLSearchParams();
      allParams.set("limit", "100"); // 获取更多视频确保完整
      allParams.set("sort_by", "max_online_today");
      allParams.set("status", "featured");

      const allRes = await fetch(`/api/user/feed?${allParams}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (allRes.ok) {
        const allData = await allRes.json();
        setAllFeaturedVideos(allData.videos || []);
      }

      // 2. 获取当前过滤后的视频（用于显示）
      const params = new URLSearchParams();
      params.set("limit", "50");
      params.set("sort_by", "max_online_today");
      params.set("status", "featured");

      if (selectedKeyword) params.set("keyword", selectedKeyword);
      if (searchQuery) params.set("search", searchQuery);

      const res = await fetch(`/api/user/feed?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setVideos(data.videos || []);
      }
    } catch (err) {
      console.error("Failed to fetch videos:", err);
    }
  }, [selectedKeyword, searchQuery]);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    await Promise.all([fetchKeywords(), fetchVideos()]);
    setIsLoading(false);
  }, [fetchKeywords, fetchVideos]);

  useEffect(() => {
    fetchUserStatus();
  }, [fetchUserStatus]);

  useEffect(() => {
    if (userStatus?.is_login) {
      loadData();
    } else if (userStatus !== null && !userStatus.is_login) {
      setIsLoading(false);
    }
  }, [userStatus, loadData]);

  useEffect(() => {
    if (userStatus?.is_login) {
      fetchVideos();
    }
  }, [userStatus, fetchVideos]);

  const addKeyword = async () => {
    if (!newKeyword.trim()) return;

    setIsAdding(true);
    try {
      const token = localStorage.getItem("bombo_token");
      const res = await fetch("/api/user/keywords", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ keyword: newKeyword.trim() }),
      });

      if (res.ok) {
        const data = await res.json();
        alert(data.message);
        setNewKeyword("");
        setShowAddModal(false);
        await loadData();
      } else {
        const error = await res.json();
        alert(error.detail || "添加失败");
      }
    } catch (err) {
      console.error("Failed to add keyword:", err);
      alert("添加失败，请稍后重试");
    } finally {
      setIsAdding(false);
    }
  };

  const deleteKeyword = async (keywordId: number) => {
    if (!confirm("确定要删除该关键词吗？")) return;

    try {
      const token = localStorage.getItem("bombo_token");
      const res = await fetch(`/api/user/keywords/${keywordId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        await loadData();
      }
    } catch (err) {
      console.error("Failed to delete keyword:", err);
    }
  };

  const refreshFeed = async () => {
    try {
      const token = localStorage.getItem("bombo_token");
      const res = await fetch("/api/user/feed/refresh", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        const data = await res.json();
        alert(data.message);
        await loadData();
      }
    } catch (err) {
      console.error("Failed to refresh feed:", err);
    }
  };

  const formatViews = (views: number) => {
    if (views >= 100000000) return (views / 100000000).toFixed(1) + "亿";
    if (views >= 10000) return (views / 10000).toFixed(1) + "w";
    return views.toString();
  };

  // Redirect tourists
  if (!isLoading && userStatus && !userStatus.is_login) {
    return (
      <div className="min-h-screen bg-[#f4f5f7] flex items-center justify-center">
        <div className="text-center px-4">
          <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mx-auto mb-4">
            <Plus className="w-8 h-8 text-gray-400" />
          </div>
          <p className="text-gray-500 mb-4">登录后使用自选赛道功能</p>
          <button
            onClick={() => router.push("/login")}
            className="px-6 py-2 bg-violet-600 text-white rounded-lg text-sm font-medium"
          >
            登录 / 注册
          </button>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#f4f5f7] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-violet-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="bg-[#f4f5f7] min-h-screen pb-20">
      {/* Header */}
      <header className="bg-violet-600 text-white safe-area-top">
        <div className="max-w-lg mx-auto">
          <div className="flex items-center justify-between px-3 py-2">
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold tracking-tight">BOMBO</span>
              <span className="text-xs bg-violet-500 px-1.5 py-0.5 rounded">我的订阅</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={refreshFeed}
                className="p-1.5 text-white/80 hover:text-white"
                title="刷新"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
              {userStatus?.is_login && (
                <div className="w-7 h-7 rounded-full bg-violet-400 flex items-center justify-center text-sm font-medium">
                  {userStatus.username?.[0]?.toUpperCase() || "U"}
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Keywords Section */}
      <div className="px-3 py-2 bg-white border-b border-gray-100">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-gray-500 font-medium">我的关键词</span>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-1 text-xs text-violet-600 font-medium"
          >
            <Plus className="w-3 h-3" />
            添加
          </button>
        </div>
        <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
          <button
            onClick={() => setSelectedKeyword("")}
            className={`flex-shrink-0 px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
              selectedKeyword === ""
                ? "bg-violet-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            全部
          </button>
          {keywords.filter(k => k.status === 1).map((kw) => (
            <div
              key={kw.id}
              className={`flex-shrink-0 px-2.5 py-1 rounded-full text-xs font-medium transition-colors flex items-center gap-1 ${
                selectedKeyword === kw.keyword
                  ? "bg-violet-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              <button
                onClick={() => setSelectedKeyword(kw.keyword)}
                className="flex items-center gap-1"
              >
                {kw.keyword}
                <span className={`text-xs ${selectedKeyword === kw.keyword ? "text-violet-200" : "text-gray-400"}`}>
                  {allFeaturedVideos.filter(v => v.keyword === kw.keyword).length}
                </span>
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  deleteKeyword(kw.id);
                }}
                className="ml-1 hover:bg-white/20 rounded-full p-0.5"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Search Bar */}
      <div className="px-3 py-2 bg-white border-b border-gray-100">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索标题或作者"
            className="w-full pl-9 pr-3 py-1.5 bg-gray-100 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
          />
        </div>
      </div>

      {/* Video List */}
      {videos.length === 0 ? (
        <div className="text-center py-20">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Plus className="w-8 h-8 text-gray-400" />
          </div>
          <p className="text-gray-500 text-sm mb-2">暂无视频</p>
          <p className="text-gray-400 text-xs">
            {keywords.length === 0 ? "添加关键词开始监控" : "尝试调整筛选条件"}
          </p>
        </div>
      ) : (
        <div className="space-y-2 px-2">
          {videos.map((video) => (
            <FeedVideoCard
              key={video.bvid}
              video={video}
              formatViews={formatViews}
            />
          ))}
        </div>
      )}

      {/* Add Keyword Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-end justify-center">
          <div className="bg-white w-full max-w-lg rounded-t-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
              <h3 className="font-medium text-gray-800">添加自选关键词</h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 space-y-4">
              <div>
                <input
                  type="text"
                  value={newKeyword}
                  onChange={(e) => setNewKeyword(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && newKeyword.trim().length >= 2) {
                      addKeyword();
                    }
                  }}
                  placeholder="输入关键词，如：化妆、穿搭、健身"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500"
                  maxLength={20}
                />
                <p className="text-xs text-gray-400 mt-1">
                  2-20个字符，不支持特殊符号
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-3 text-xs text-gray-500 space-y-1">
                <p className="font-medium text-gray-700">添加后系统将自动：</p>
                <p>• 立即搜索B站当前热门视频</p>
                <p>• 自动筛选播放&gt;3000且点赞&gt;100的优质视频</p>
                <p>• 每日自动刷新，持续追踪新视频</p>
                <p>• 每小时更新一次监控数据</p>
              </div>

              <button
                onClick={addKeyword}
                disabled={isAdding || newKeyword.trim().length < 2}
                className="w-full py-2.5 bg-violet-600 text-white rounded-lg text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isAdding ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <Plus className="w-4 h-4" />
                    确认添加
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface FeedVideoCardProps {
  video: FeedVideo;
  formatViews: (views: number) => string;
}

function FeedVideoCard({ video, formatViews }: FeedVideoCardProps) {
  const router = useRouter();

  const handleCardClick = () => {
    router.push(`/m/video/${video.bvid}`);
  };

  const handleJumpToBilibili = (e: React.MouseEvent) => {
    e.stopPropagation();
    window.open(`https://www.bilibili.com/video/${video.bvid}`, "_blank");
  };

  // 使用后端代理获取封面图片，解决B站防盗链403问题
  const secureCoverUrl = video.cover_url?.replace(/^http:\/\//i, "https://");
  const coverProxyUrl = secureCoverUrl
    ? `/api/videos/cover-proxy?url=${encodeURIComponent(secureCoverUrl)}`
    : null;

  return (
    <div
      className={`bg-white rounded-lg shadow-sm overflow-hidden flex relative ${
        video.view_yesterday && video.view_today > video.view_yesterday * 1.3
          ? "border-2 border-orange-400"
          : ""
      }`}
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
          <span className="text-xs text-violet-500 truncate max-w-[60px]">#{video.keyword}</span>
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
            {video.first_seen ? (
              (() => {
                const diff = Date.now() - new Date(video.first_seen).getTime();
                const hours = Math.floor(diff / (1000 * 60 * 60));
                const days = Math.floor(hours / 24);
                if (hours < 1) return '刚刚';
                if (hours < 24) return `${hours}小时前`;
                if (days < 30) return `${days}天前`;
                return new Date(video.first_seen).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
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
