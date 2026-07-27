"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Search, ArrowLeft, Users } from "lucide-react";

interface Video {
  bvid: string;
  title: string;
  author: string;
  channel: string;
  cover_url?: string;
  view_today: number;
  author_fans?: number;
}

interface Author {
  name: string;
  mid: string;
  fans: number;
  video_count: number;
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [videos, setVideos] = useState<Video[]>([]);
  const [authors, setAuthors] = useState<Author[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const router = useRouter();

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsLoading(true);
    setHasSearched(true);

    try {
      const res = await fetch(`/api/videos/search?q=${encodeURIComponent(query)}&limit=20`);
      if (res.ok) {
        const data = await res.json();
        setVideos(data.videos || []);
        setAuthors(data.authors || []);
      }
    } catch (err) {
      console.error("Search failed:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const formatViews = (views: number) => {
    if (views >= 100000000) return (views / 100000000).toFixed(1) + "亿";
    if (views >= 10000) return (views / 10000).toFixed(1) + "w";
    return views.toString();
  };

  const formatFans = (fans: number) => {
    if (fans >= 100000000) return (fans / 100000000).toFixed(1) + "亿";
    if (fans >= 10000) return (fans / 10000).toFixed(1) + "万";
    return fans.toString();
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Search Header */}
      <header className="bg-blue-600 text-white sticky top-0 z-50">
        <div className="max-w-lg mx-auto">
          <div className="flex items-center gap-2 px-3 py-2">
            <button onClick={() => router.back()} className="p-1">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <form onSubmit={handleSearch} className="flex-1 flex items-center bg-blue-500 rounded-full px-4 py-1.5">
              <Search className="w-4 h-4 text-blue-200 mr-2" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="搜索热门视频、UP主"
                className="flex-1 bg-transparent text-white text-sm placeholder-blue-200 outline-none"
                autoFocus
              />
            </form>
          </div>
        </div>
      </header>

      {/* Search Results */}
      <div className="max-w-lg mx-auto">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : !hasSearched ? (
          <div className="text-center py-20">
            <Search className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-400">搜索上榜视频和博主</p>
          </div>
        ) : videos.length === 0 && authors.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-gray-400">未找到相关结果</p>
          </div>
        ) : (
          <div className="p-3 space-y-4">
            {/* Authors Section */}
            {authors.length > 0 && (
              <div>
                <h2 className="text-sm font-medium text-gray-500 mb-2 flex items-center gap-1">
                  <Users className="w-4 h-4" />
                  相关博主
                </h2>
                <div className="space-y-2">
                  {authors.map((author) => (
                    <div
                      key={author.mid || author.name}
                      className="bg-white rounded-lg p-3 flex items-center gap-3"
                    >
                      <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-medium">
                        {author.name[0]?.toUpperCase()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-gray-800 truncate">{author.name}</p>
                        <p className="text-xs text-gray-500">{formatFans(author.fans)}粉丝 · {author.video_count}个上榜视频</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Videos Section */}
            {videos.length > 0 && (
              <div>
                <h2 className="text-sm font-medium text-gray-500 mb-2">
                  相关视频 ({videos.length})
                </h2>
                <div className="space-y-2">
                  {videos.map((video) => {
                    const secureCoverUrl = video.cover_url?.replace(/^http:\/\//i, "https://");
                    const coverProxyUrl = secureCoverUrl
                      ? `/api/videos/cover-proxy?url=${encodeURIComponent(secureCoverUrl)}`
                      : null;

                    return (
                      <Link
                        key={video.bvid}
                        href={`/m/video/${video.bvid}`}
                        className="bg-white rounded-lg p-2 flex gap-2"
                      >
                        <div className="w-24 h-16 bg-gray-100 rounded flex-shrink-0 overflow-hidden">
                          {coverProxyUrl ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img src={coverProxyUrl} alt={video.title} className="w-full h-full object-cover" />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center text-gray-400 text-xs">暂无封面</div>
                          )}
                        </div>
                        <div className="flex-1 min-w-0 flex flex-col justify-center">
                          <h3 className="text-sm font-medium text-gray-800 line-clamp-2">{video.title}</h3>
                          <p className="text-xs text-gray-500 mt-1">{video.author} · {formatViews(video.view_today)}播放</p>
                        </div>
                      </Link>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
