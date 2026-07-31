"use client";

import { useDashboardStats, useBrowseStats } from "@/hooks/useApi";
import { Header } from "@/components/Header";
import { StatCard } from "@/components/StatCard";
import { TrendChart } from "@/components/TrendChart";
import { Video, BarChart3, TrendingUp, Clock } from "lucide-react";

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: browseStats } = useBrowseStats();

  // 从API获取用户增长数据
  const userGrowthData = stats?.user_growth?.map((item) => item.count) ?? [];
  const userGrowthLabels = stats?.user_growth?.map((item) => item.date) ?? [];

  // 从API获取浏览数据
  const browseData = browseStats?.browse_trend?.map((item) => item.count) ?? [];
  const browseLabels = browseStats?.browse_trend?.map((item) => item.date) ?? [];

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
            title="AI分析视频"
            value={stats?.ai_analyzed ?? "-"}
            icon={BarChart3}
            subtitle="已完成AI分析的视频"
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
              title="用户数量增长趋势"
              data={userGrowthData}
              labels={userGrowthLabels}
            />
          </div>
          <div className="card p-6">
            <TrendChart
              title="用户浏览次数趋势"
              data={browseData}
              labels={browseLabels}
            />
          </div>
        </div>
      </div>
    </>
  );
}
