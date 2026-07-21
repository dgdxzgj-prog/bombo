"use client";

import { useState, useEffect } from "react";
import { TrendingUp, TrendingDown, DollarSign, BarChart3, PieChart, Calendar } from "lucide-react";
import { Header } from "@/components/Header";

interface CostSummary {
  today: {
    total_cost: number;
    total_calls: number;
    by_type: Array<{
      analysis_type: string;
      call_count: number;
      total_cost: number;
    }>;
  };
  yesterday: {
    total_cost: number;
    total_calls: number;
  };
  this_month: {
    year: number;
    month: number;
    total_cost: number;
    total_calls: number;
    daily: Array<{
      date: string;
      call_count: number;
      cost: number;
    }>;
  };
  estimated_revenue: number;
  estimated_profit: number;
  gross_profit_rate: number;
}

export default function CostPage() {
  const [summary, setSummary] = useState<CostSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadCostSummary();
    loadMyCost();
  }, []);

  const loadCostSummary = async () => {
    try {
      const token = localStorage.getItem("bombo_token");
      if (!token) {
        setError("请先登录");
        setIsLoading(false);
        return;
      }

      const res = await fetch("/api/cost/summary", {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        const data = await res.json();
        setSummary(data);
      }
      // 即使403也不设置error，让页面继续显示其他内容
    } catch (err) {
      console.error("Failed to load cost summary:", err);
    }
  };

  const loadMyCost = async () => {
    try {
      const token = localStorage.getItem("bombo_token");
      if (!token) return;

      const res = await fetch("/api/cost/my?days=30", {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        const data = await res.json();
        // 可以在这里处理用户的个人成本数据
        console.log("My cost:", data);
      }
    } catch (err) {
      console.error("Failed to load my cost:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const getAnalysisTypeName = (type: string) => {
    const names: Record<string, string> = {
      cover_analysis: "封面分析",
      content_analysis: "内容分析",
      frame_extract: "抽帧分析",
      compare_diagnose: "对标诊断",
      commercial_report: "商业化报告",
    };
    return names[type] || type;
  };

  const formatCurrency = (amount: number) => {
    return `¥${amount.toFixed(4)}`;
  };

  if (isLoading) {
    return (
      <>
        <Header title="成本统计" subtitle="AI模型调用成本分析" />
        <div className="p-6 flex items-center justify-center h-64">
          <div className="text-dark-textMuted">加载中...</div>
        </div>
      </>
    );
  }

  // 没有数据时的友好提示
  const hasNoData = !summary || !summary.today || !summary.this_month;

  const todayVsYesterday = summary?.yesterday?.total_cost > 0
    ? ((summary.today.total_cost - summary.yesterday.total_cost) / summary.yesterday.total_cost * 100).toFixed(1)
    : "0";

  return (
    <>
      <Header title="成本统计" subtitle="AI模型调用成本分析" />

      <div className="p-6 max-w-7xl mx-auto">
        {/* No Data / No Permission Notice */}
        {hasNoData && (
          <div className="mb-6 p-4 bg-dark-bg rounded-lg border border-dark-border">
            <p className="text-dark-textMuted text-center">
              暂无成本数据或您没有管理员权限查看完整统计。
            </p>
            <p className="text-dark-textMuted text-center text-sm mt-1">
              成本数据将在AI分析功能使用后自动统计。
            </p>
          </div>
        )}

        {/* Summary Cards */}
        {!hasNoData && summary && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            {/* 今日成本 */}
            <div className="card p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-dark-textMuted text-sm">今日成本</span>
                <DollarSign className="w-4 h-4 text-dark-textMuted" />
              </div>
              <p className="text-2xl font-bold text-white">
                {formatCurrency(summary.today.total_cost)}
              </p>
              <div className="flex items-center mt-1">
                {parseFloat(todayVsYesterday) >= 0 ? (
                  <TrendingUp className="w-3 h-3 text-red-400 mr-1" />
                ) : (
                  <TrendingDown className="w-3 h-3 text-green-400 mr-1" />
                )}
                <span className={`text-xs ${parseFloat(todayVsYesterday) >= 0 ? "text-red-400" : "text-green-400"}`}>
                  {parseFloat(todayVsYesterday) >= 0 ? "+" : ""}{todayVsYesterday}%
                </span>
                <span className="text-dark-textMuted text-xs ml-1">vs昨日</span>
              </div>
            </div>

            {/* 今日调用次数 */}
            <div className="card p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-dark-textMuted text-sm">今日调用</span>
                <BarChart3 className="w-4 h-4 text-dark-textMuted" />
              </div>
              <p className="text-2xl font-bold text-white">
                {summary.today.total_calls}
              </p>
              <p className="text-dark-textMuted text-xs mt-1">次AI分析</p>
            </div>

            {/* 本月成本 */}
            <div className="card p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-dark-textMuted text-sm">本月成本</span>
                <Calendar className="w-4 h-4 text-dark-textMuted" />
              </div>
              <p className="text-2xl font-bold text-white">
                {formatCurrency(summary.this_month.total_cost)}
              </p>
              <p className="text-dark-textMuted text-xs mt-1">
                {summary.this_month.year}年{summary.this_month.month}月
              </p>
            </div>

            {/* 预估收益 */}
            <div className="card p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-dark-textMuted text-sm">预估收益</span>
                <PieChart className="w-4 h-4 text-dark-textMuted" />
              </div>
              <p className="text-2xl font-bold text-green-400">
                {formatCurrency(summary.estimated_profit)}
              </p>
              <p className="text-dark-textMuted text-xs mt-1">
                毛利率{(summary.gross_profit_rate * 100).toFixed(0)}%
              </p>
            </div>
          </div>
        )}

        {/* Cost by Type */}
        {summary && summary.today && (
          <div className="card p-6 mb-6">
            <h2 className="text-lg font-bold text-white mb-4">今日成本分布</h2>
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              {summary.today.by_type && summary.today.by_type.length > 0 ? (
                summary.today.by_type.map((item) => (
                  <div key={item.analysis_type} className="bg-dark-bg rounded-lg p-4">
                    <p className="text-dark-textMuted text-sm mb-1">
                      {getAnalysisTypeName(item.analysis_type)}
                    </p>
                    <p className="text-xl font-bold text-white">
                      {formatCurrency(item.total_cost)}
                    </p>
                    <p className="text-dark-textMuted text-xs mt-1">
                      {item.call_count}次调用
                    </p>
                  </div>
                ))
              ) : (
                <div className="col-span-5 text-center py-8 text-dark-textMuted">
                  暂无数据
                </div>
              )}
            </div>
          </div>
        )}

        {/* Monthly Trend */}
        {summary && summary.this_month && (
          <div className="card p-6">
            <h2 className="text-lg font-bold text-white mb-4">本月每日成本趋势</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-dark-border">
                    <th className="text-left py-2 px-4 text-dark-textMuted text-sm">日期</th>
                    <th className="text-right py-2 px-4 text-dark-textMuted text-sm">调用次数</th>
                    <th className="text-right py-2 px-4 text-dark-textMuted text-sm">成本</th>
                    <th className="text-right py-2 px-4 text-dark-textMuted text-sm">占比</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.this_month.daily && summary.this_month.daily.length > 0 ? (
                    summary.this_month.daily.map((day) => {
                      const percentage = summary.this_month.total_cost > 0
                        ? (day.cost / summary.this_month.total_cost * 100).toFixed(1)
                        : "0";
                      return (
                        <tr key={day.date} className="border-b border-dark-border/50 hover:bg-dark-bg/50">
                        <td className="py-2 px-4 text-white">{day.date}</td>
                        <td className="py-2 px-4 text-right text-white">{day.call_count}</td>
                        <td className="py-2 px-4 text-right text-white">{formatCurrency(day.cost)}</td>
                        <td className="py-2 px-4 text-right text-dark-textMuted">{percentage}%</td>
                      </tr>
                    )
                  })
                ) : (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-dark-textMuted">
                      暂无数据
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          </div>
        )}

        {/* Cost Formula Reference */}
        <div className="mt-6 p-4 bg-dark-bg rounded-lg border border-dark-border">
          <h3 className="text-sm font-medium text-white mb-2">成本计算公式</h3>
          <p className="text-dark-textMuted text-xs">
            豆包Doubao-Seed-2.0-lite: 输入 0.6元/百万tokens，输出 3.6元/百万tokens
          </p>
          <ul className="mt-2 text-xs text-dark-textMuted space-y-1">
            <li>• 封面分析: ~1000输入 + ~300输出 = ¥0.00168/次</li>
            <li>• 8帧抽帧分析: ~8000输入 + ~1000输出 = ¥0.009/次</li>
            <li>• 双视频对标诊断: ~16000输入 + ~2500输出 = ¥0.018/次</li>
          </ul>
        </div>
      </div>
    </>
  );
}
