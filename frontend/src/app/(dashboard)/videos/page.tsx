"use client";

import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import Link from "next/link";
import { Search, Loader2 } from "lucide-react";
import clsx from "clsx";

interface Channel {
  channel_id: string;
  channel_name: string;
}

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
  pubdate?: string;
  author_fans?: number;
  duration?: number;
}

const PAGE_SIZE = 40;

function formatNumber(num: number): string {
  if (num >= 100000000) {
    return (num / 100000000).toFixed(1) + "亿";
  }
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + "万";
  }
  return num.toLocaleString();
}

function formatViews(views: number): string {
  if (views >= 100000000) return (views / 100000000).toFixed(1) + "亿";
  if (views >= 10000) return (views / 10000).toFixed(1) + "万";
  return views.toString();
}

export default function VideosPage() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [selectedChannel, setSelectedChannel] = useState("");
  const [videos, setVideos] = useState<Video[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);

  // 获取赛道列表
  useEffect(() => {
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
    fetchChannels();
  }, []);

  // 获取视频列表
  const fetchVideos = useCallback(async (reset: boolean = false, pageNum?: number) => {
    try {
      const token = localStorage.getItem("bombo_token");
      const headers: HeadersInit = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const currentPage = reset ? 0 : (pageNum !== undefined ? pageNum : page);
      const offset = currentPage * PAGE_SIZE;

      const url = selectedChannel
        ? `/api/videos/featured?channel=${encodeURIComponent(selectedChannel)}&limit=${PAGE_SIZE}&offset=${offset}`
        : `/api/videos/featured?limit=${PAGE_SIZE}&offset=${offset}`;

      const res = await fetch(url, { headers });

      if (!res.ok) {
        throw new Error("Failed to fetch videos");
      }

      const data = await res.json();
      const newVideos = data.videos || [];

      if (reset) {
        setVideos(newVideos);
        setPage(0);
      } else {
        setVideos((prev) => [...prev, ...newVideos]);
      }

      setHasMore(newVideos.length === PAGE_SIZE);
    } catch (err) {
      console.error("Failed to fetch videos:", err);
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  }, [page, selectedChannel]);

  // 初始加载和筛选变化时重置
  useEffect(() => {
    setIsLoading(true);
    setPage(0);
    fetchVideos(true).finally(() => setIsLoading(false));
  }, [selectedChannel]);

  // 加载更多
  const loadMore = async () => {
    if (isLoadingMore || !hasMore) return;
    setIsLoadingMore(true);
    const nextPage = page + 1;
    setPage(nextPage);
    await fetchVideos(false, nextPage);
    setIsLoadingMore(false);
  };

  // 滚动监听加载更多
  useEffect(() => {
    const handleScroll = () => {
      if (!listRef.current) return;
      const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
      if (scrollTop + clientHeight >= scrollHeight - 200) {
        loadMore();
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, [hasMore, isLoadingMore]);

  const filteredVideos = useMemo(() => {
    if (!search) return videos;
    const keyword = search.toLowerCase();
    return videos.filter(
      (v) =>
        v.title.toLowerCase().includes(keyword) ||
        v.author.toLowerCase().includes(keyword)
    );
  }, [videos, search]);

  return (
    <>
      <div className="flex items-center p-6 pb-0">
        <div>
          <h1 className="text-2xl font-bold text-white">全网爆款</h1>
          <p className="text-dark-textMuted mt-1">全网热门视频榜单</p>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* 赛道筛选 */}
        <div className="card p-4">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setSelectedChannel("")}
              className={clsx(
                "px-3 py-1.5 rounded-full text-sm font-medium transition",
                selectedChannel === ""
                  ? "bg-primary-600 text-white"
                  : "bg-dark-bg text-dark-textMuted hover:bg-dark-border hover:text-white"
              )}
            >
              全部
            </button>
            {channels.map((channel) => (
              <button
                key={channel.channel_id}
                onClick={() => setSelectedChannel(channel.channel_name)}
                className={clsx(
                  "px-3 py-1.5 rounded-full text-sm font-medium transition",
                  selectedChannel === channel.channel_name
                    ? "bg-primary-600 text-white"
                    : "bg-dark-bg text-dark-textMuted hover:bg-dark-border hover:text-white"
                )}
              >
                {channel.channel_name}
              </button>
            ))}
          </div>
        </div>

        {/* 搜索框 */}
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-dark-textMuted" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索视频或作者..."
            className="input pl-12 w-full max-w-md"
          />
        </div>

        {/* 视频列表 */}
        <div className="card p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-white">
              视频列表 ({filteredVideos.length})
            </h2>
            <span className="text-sm text-dark-textMuted">
              {hasMore ? "滚动加载更多" : "已加载全部"}
            </span>
          </div>

          {isLoading ? (
            <div className="p-8 animate-pulse text-center text-dark-textMuted">
              <Loader2 className="w-8 h-8 mx-auto animate-spin text-primary-400 mb-2" />
              加载中...
            </div>
          ) : error ? (
            <div className="p-8 text-center text-red-400">
              加载失败: {error}
            </div>
          ) : filteredVideos.length === 0 ? (
            <div className="p-8 text-center text-dark-textMuted">
              暂无视频数据
            </div>
          ) : (
            <div ref={listRef} className="grid grid-cols-4 gap-4">
              {filteredVideos.map((video: Video) => {
                const displayViews = video.view_yesterday || video.view_today;
                const coverUrl = typeof video.cover_url === "string" ? video.cover_url : null;
                const secureCoverUrl = coverUrl?.replace(/^http:\/\//i, "https://");
                const coverProxyUrl = secureCoverUrl
                  ? `/api/videos/cover-proxy?url=${encodeURIComponent(secureCoverUrl)}`
                  : null;

                return (
                  <Link
                    key={video.bvid}
                    href={`/videos/${video.bvid}`}
                    className="group block bg-dark-bg rounded-lg overflow-hidden hover:ring-2 hover:ring-primary-500 transition-all"
                  >
                    <div className="relative aspect-video bg-dark-border">
                      {coverProxyUrl ? (
                        <img
                          src={coverProxyUrl}
                          alt={video.title}
                          className="w-full h-full object-cover"
                          crossOrigin="anonymous"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-dark-textMuted">
                          暂无封面
                        </div>
                      )}

                      <div className="absolute top-2 right-2 flex flex-col gap-1">
                        <span
                          className={clsx(
                            "px-2 py-0.5 rounded-full text-xs font-bold border-2",
                            (video.online_count || 0) >= 10000
                              ? "bg-red-500 text-white border-red-500"
                              : (video.online_count || 0) >= 1000
                              ? "bg-orange-500 text-white border-orange-500"
                              : "bg-yellow-500 text-white border-yellow-500"
                          )}
                        >
                          {formatNumber(video.online_count || 0)}
                        </span>
                      </div>

                      {video.duration && video.duration > 0 && (
                        <div className="absolute bottom-2 right-2 px-1.5 py-0.5 rounded bg-black/70 text-white text-xs font-medium">
                          {(() => {
                            const h = Math.floor(video.duration! / 3600);
                            const m = Math.floor((video.duration! % 3600) / 60);
                            const s = video.duration! % 60;
                            if (h > 0) return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
                            return `${m}:${s.toString().padStart(2, "0")}`;
                          })()}
                        </div>
                      )}
                    </div>

                    <div className="p-3">
                      <h3 className="text-white text-sm font-medium line-clamp-2 mb-2 group-hover:text-primary-400 transition-colors">
                        {video.title}
                      </h3>

                      <p className="text-dark-textMuted text-xs mb-1 truncate">
                        {video.author}
                      </p>

                      <div className="flex items-center justify-between text-xs">
                        <span className="text-dark-textMuted">
                          {formatViews(displayViews)}播放
                        </span>
                        {video.author_fans ? (
                          <span className="text-dark-textMuted">
                            {formatViews(video.author_fans)}粉丝
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}

          {isLoadingMore && (
            <div className="p-4 text-center text-dark-textMuted">
              <Loader2 className="w-6 h-6 mx-auto animate-spin text-primary-400 mb-2" />
              加载更多...
            </div>
          )}
        </div>
      </div>
    </>
  );
}