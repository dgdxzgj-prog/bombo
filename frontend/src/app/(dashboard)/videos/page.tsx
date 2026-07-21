"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import clsx from "clsx";

const CHANNEL_OPTIONS = [
  { value: "", label: "全部赛道" },
  { value: "动画", label: "动画" },
  { value: "音乐", label: "音乐" },
  { value: "游戏", label: "游戏" },
  { value: "娱乐", label: "娱乐" },
  { value: "影视", label: "影视" },
  { value: "番剧", label: "番剧" },
  { value: "电影", label: "电影" },
  { value: "鬼畜", label: "鬼畜" },
  { value: "舞蹈", label: "舞蹈" },
  { value: "生活", label: "生活" },
  { value: "国创", label: "国创" },
  { value: "纪录片", label: "纪录片" },
  { value: "科技", label: "科技" },
  { value: "资讯", label: "资讯" },
  { value: "知识", label: "知识" },
  { value: "美食", label: "美食" },
  { value: "动物圈", label: "动物圈" },
  { value: "汽车", label: "汽车" },
  { value: "运动", label: "运动" },
  { value: "时尚", label: "时尚" },
  { value: "软件应用", label: "软件应用" },
];

const MATURITY_THRESHOLD_HOURS = 24;

interface Video {
  bvid: string;
  title: string;
  author: string;
  channel: string;
  cover_url: string;
  view_yesterday: number;
  view_today: number;
  growth_rate: number;
  like_count: number;
  online_count: number;
  first_seen: string;
  status: string;
}

function formatNumber(num: number): string {
  if (num >= 100000000) {
    return (num / 100000000).toFixed(1) + "亿";
  }
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + "万";
  }
  return num.toLocaleString();
}

function isMatureVideo(firstSeen: string): boolean {
  const firstSeenTime = new Date(firstSeen).getTime();
  const now = Date.now();
  const hoursElapsed = (now - firstSeenTime) / (1000 * 60 * 60);
  return hoursElapsed >= MATURITY_THRESHOLD_HOURS;
}

export default function VideosPage() {
  const [channel, setChannel] = useState("");
  const [search, setSearch] = useState("");
  const [videos, setVideos] = useState<Video[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("http://localhost:8000/api/videos/featured?limit=100")
      .then((res) => res.json())
      .then((data) => {
        setVideos(data.videos || []);
        setIsLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setIsLoading(false);
      });
  }, []);

  const filteredVideos = useMemo(() => {
    let result = [...videos];

    if (channel) {
      result = result.filter((v) => v.channel === channel);
    }

    if (search) {
      const keyword = search.toLowerCase();
      result = result.filter(
        (v) =>
          v.title.toLowerCase().includes(keyword) ||
          v.author.toLowerCase().includes(keyword)
      );
    }

    result.sort((a, b) => (b.online_count || 0) - (a.online_count || 0));

    return result;
  }, [videos, channel, search]);

  return (
    <>
      <div className="flex items-center p-6 pb-0">
        <div>
          <h1 className="text-2xl font-bold text-white">全网爆款</h1>
          <p className="text-dark-textMuted mt-1">全网热门视频榜单</p>
        </div>
      </div>

      <div className="p-6 space-y-6">
        <div className="card p-4">
          <div className="flex flex-wrap gap-2">
            {CHANNEL_OPTIONS.map((option) => (
              <button
                key={option.value}
                onClick={() => setChannel(option.value)}
                className={clsx(
                  "px-3 py-1.5 rounded-full text-sm font-medium transition",
                  channel === option.value
                    ? "bg-primary-600 text-white"
                    : "bg-dark-bg text-dark-textMuted hover:bg-dark-border hover:text-white"
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

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

        <div className="card p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-white">
              视频列表 ({filteredVideos.length})
            </h2>
            <span className="text-sm text-dark-textMuted">
              排序：在线人数降序
            </span>
          </div>

          {isLoading ? (
            <div className="p-8 animate-pulse text-center text-dark-textMuted">
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
            <div className="grid grid-cols-4 gap-4">
              {filteredVideos.map((video: Video) => {
                const mature = isMatureVideo(video.first_seen);
                const displayViews = video.view_yesterday || video.view_today;

                return (
                  <Link
                    key={video.bvid}
                    href={`/videos/${video.bvid}`}
                    className="group block bg-dark-bg rounded-lg overflow-hidden hover:ring-2 hover:ring-primary-500 transition-all"
                  >
                    <div className="relative aspect-video bg-dark-border">
                      {video.cover_url ? (
                        <img
                          src={"http://localhost:8000/api/videos/cover-proxy?url=" + encodeURIComponent(video.cover_url)}
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
                          {formatNumber(displayViews)}播放
                        </span>
                        <span className="text-dark-textMuted">
                          {formatNumber(video.like_count)}点赞
                        </span>
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
