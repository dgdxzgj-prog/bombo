"use client";

import { useDashboardStats, useDashboardFeaturedVideos } from "@/hooks/useApi";
import { Header } from "@/components/Header";
import { StatCard } from "@/components/StatCard";
import { TrendChart } from "@/components/TrendChart";
import { ChannelChart } from "@/components/ChannelChart";
import { Video, BarChart3, TrendingUp, Clock } from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: featured, isLoading: featuredLoading } = useDashboardFeaturedVideos(10);

  // Generate mock trend data for chart (in real app, this would come from API)
  const trendData = [65, 72, 68, 85, 92, 88, 95, 102, 98, 110];
  const trendLabels = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月"];

  // Mock channel distribution data
  const channelData = stats
    ? [
        { name: "娱乐", value: 156 },
        { name: "游戏", value: 132 },
        { name: "科技", value: 98 },
        { name: "生活", value: 87 },
        { name: "美食", value: 65 },
      ]
    : [];

  return (
    <>
      <Header title="控制台" subtitle="B站视频热度监控系统" />

      <div className="p-6 space-y-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard
            title="监控中视频"
            value={stats?.videos.monitoring ?? "-"}
            icon={Video}
            subtitle="正在追踪的视频"
          />
          <StatCard
            title="已上榜爆款"
            value={stats?.videos.featured ?? "-"}
            icon={TrendingUp}
            subtitle="累计识别爆款"
          />
          <StatCard
            title="赛道数量"
            value={stats?.channels.total ?? "-"}
            icon={BarChart3}
            subtitle={`${stats?.channels.locked ?? 0} 个已锁定`}
          />
          <StatCard
            title="更新时间"
            value={stats?.timestamp ? new Date(stats.timestamp).toLocaleTimeString() : "-"}
            icon={Clock}
            subtitle="数据更新时间"
          />
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card p-6">
            <TrendChart
              title="播放量趋势"
              data={trendData}
              labels={trendLabels}
            />
          </div>
          <div className="card p-6">
            <ChannelChart
              title="赛道热度分布"
              data={channelData}
            />
          </div>
        </div>

        {/* Featured Videos */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-white">爆款视频 TOP 10</h2>
            <Link href="/videos" className="link text-sm">
              查看全部 →
            </Link>
          </div>

          {featuredLoading ? (
            <div className="animate-pulse space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-16 bg-dark-border rounded-lg" />
              ))}
            </div>
          ) : featured?.videos.length ? (
            <div className="space-y-3">
              {featured.videos.map((video, index) => (
                <Link
                  key={video.bvid}
                  href={`/videos/${video.bvid}`}
                  className="flex items-center justify-between p-4 bg-dark-bg hover:bg-dark-border rounded-lg transition"
                >
                  <div className="flex items-center gap-4">
                    <span
                      className={`w-8 h-8 flex items-center justify-center rounded-full text-sm font-bold ${
                        index < 3
                          ? "bg-primary-600 text-white"
                          : "bg-dark-border text-dark-textMuted"
                      }`}
                    >
                      {index + 1}
                    </span>
                    <div>
                      <p className="text-white font-medium line-clamp-1">
                        {video.title}
                      </p>
                      <p className="text-sm text-dark-textMuted">
                        {video.author} · {video.channel}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-emerald-400 font-bold">
                      +{video.growth_rate}%
                    </p>
                    <p className="text-sm text-dark-textMuted">
                      {video.view_today.toLocaleString()} 播放
                    </p>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-dark-textMuted">
              暂无爆款视频数据
            </div>
          )}
        </div>
      </div>
    </>
  );
}
