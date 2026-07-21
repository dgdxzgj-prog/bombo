"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useFeaturedVideos } from "@/hooks/useApi";
import { TrendingUp, Eye, ThumbsUp, MessageSquare, Search } from "lucide-react";
import clsx from "clsx";

const CHANNEL_OPTIONS = [
  { value: "", label: "全部" },
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

export default function HomePage() {
  const [channel, setChannel] = useState("");
  const [searchText, setSearchText] = useState("");
  const [mounted, setMounted] = useState(false);

  const { data, isLoading } = useFeaturedVideos({
    channel: channel || undefined,
    limit: 100,
  });

  useEffect(() => {
    setMounted(true);
  }, []);

  // 按热度（播放量）降序排序
  const sortedVideos = data?.videos
    ? [...data.videos].sort((a, b) => (b.view_today || 0) - (a.view_today || 0))
    : [];

  // 过滤搜索
  const filteredVideos = searchText
    ? sortedVideos.filter(
        (v) =>
          v.title?.toLowerCase().includes(searchText.toLowerCase()) ||
          v.author?.toLowerCase().includes(searchText.toLowerCase())
      )
    : sortedVideos;

  if (!mounted) {
    return (
      <div className="min-h-screen bg-[#f4f5f7]">
        <div className="max-w-[1400px] mx-auto p-4">
          <div className="animate-pulse text-gray-400">加载中...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f4f5f7]">
      {/* 顶部导航 */}
      <div className="bg-white shadow-sm sticky top-0 z-50">
        <div className="max-w-[1400px] mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <Link href="/" className="text-xl font-bold text-pink-500 hover:text-pink-600">
              BOMBO
            </Link>
            <div className="flex items-center gap-4">
              <Link
                href="/dashboard"
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                管理后台
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* 搜索栏 */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-[1400px] mx-auto px-4 py-3">
          <div className="flex items-center gap-4">
            {/* 搜索框 */}
            <div className="relative flex-1 max-w-[600px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                placeholder="搜索视频或UP主..."
                className="w-full pl-10 pr-4 py-2 bg-gray-100 rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-pink-500 focus:bg-white transition"
              />
            </div>
          </div>
        </div>
      </div>

      {/* 赛道筛选 */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-[1400px] mx-auto px-4 py-3">
          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            <span className="text-sm text-gray-500 whitespace-nowrap">赛道:</span>
            {CHANNEL_OPTIONS.map((option) => (
              <button
                key={option.value}
                onClick={() => setChannel(option.value)}
                className={clsx(
                  "px-3 py-1 rounded text-sm whitespace-nowrap transition",
                  channel === option.value
                    ? "bg-pink-500 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 内容区域 */}
      <div className="max-w-[1400px] mx-auto px-4 py-6">
        {/* 结果统计 */}
        <div className="flex items-center justify-between mb-4">
          <p className="text-gray-500 text-sm">
            {isLoading ? "加载中..." : `${filteredVideos.length} 个视频`}
            {channel && ` · ${CHANNEL_OPTIONS.find(c => c.value === channel)?.label}`}
            {searchText && ` · 搜索: ${searchText}`}
          </p>
        </div>

        {/* 视频网格 - B站风格 */}
        {isLoading ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-4">
            {[...Array(10)].map((_, i) => (
              <div key={i} className="bg-white rounded-lg overflow-hidden animate-pulse shadow-sm">
                <div className="aspect-video bg-gray-200" />
                <div className="p-3 space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-full" />
                  <div className="h-3 bg-gray-200 rounded w-2/3" />
                </div>
              </div>
            ))}
          </div>
        ) : filteredVideos.length === 0 ? (
          <div className="text-center py-16">
            <div className="text-gray-300 text-6xl mb-4">📺</div>
            <p className="text-gray-500">暂无上榜视频</p>
            <p className="text-gray-400 text-sm mt-1">稍后再来看看吧</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-4">
            {filteredVideos.map((video) => (
              <Link
                key={video.bvid}
                href={`/video/${video.bvid}`}
                className="bg-white rounded-lg overflow-hidden hover:shadow-lg transition group"
              >
                {/* 封面 */}
                <div className="relative aspect-video bg-gray-100">
                  {video.cover_url ? (
                    <img
                      src={video.cover_url}
                      alt={video.title}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-400">
                      无封面
                    </div>
                  )}
                  {/* 播放量标签 */}
                  <div className="absolute bottom-1 right-1 bg-black/70 text-white text-xs px-1.5 py-0.5 rounded flex items-center gap-1">
                    <Eye className="w-3 h-3" />
                    {video.view_today ? (video.view_today >= 10000 ? Math.round(video.view_today / 10000) + '万' : video.view_today) : '0'}
                  </div>
                  {/* 爆款标签 */}
                  {video.status === 'featured' && (
                    <div className="absolute top-1 left-1 bg-red-500 text-white text-xs px-1.5 py-0.5 rounded font-medium">
                      爆
                    </div>
                  )}
                </div>

                {/* 信息 */}
                <div className="p-2">
                  <h3 className="text-gray-800 text-sm font-medium line-clamp-2 mb-1 group-hover:text-pink-500 transition">
                    {video.title || '无标题'}
                  </h3>
                  <p className="text-gray-500 text-xs mb-2">
                    {video.author || '未知作者'}
                  </p>

                  {/* 底部信息 */}
                  <div className="flex items-center justify-between text-xs text-gray-400">
                    <span className="flex items-center gap-1">
                      <ThumbsUp className="w-3 h-3" />
                      {video.like_count ? (video.like_count >= 10000 ? Math.round(video.like_count / 10000) + '万' : video.like_count) : '0'}
                    </span>
                    <span className="flex items-center gap-1">
                      <MessageSquare className="w-3 h-3" />
                      {video.reply_count || '0'}
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
