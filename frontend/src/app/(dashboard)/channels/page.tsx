"use client";

import { useState } from "react";
import { useChannels, useUpdateChannelSortOrder } from "@/hooks/useApi";
import { Header } from "@/components/Header";
import { RefreshCw, Save } from "lucide-react";
import clsx from "clsx";

export default function ChannelsPage() {
  const { data, isLoading, error, refetch } = useChannels();
  const updateSortOrderMutation = useUpdateChannelSortOrder();
  const [editingSortOrders, setEditingSortOrders] = useState<Record<string, number>>({});
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set());

  if (isLoading) {
    return (
      <>
        <Header title="赛道配置" />
        <div className="p-6 flex items-center justify-center h-64">
          <div className="animate-pulse text-dark-textMuted">加载中...</div>
        </div>
      </>
    );
  }

  if (error || !data) {
    return (
      <>
        <Header title="赛道配置" />
        <div className="p-6 flex items-center justify-center h-64">
          <div className="text-red-400">加载失败，请刷新页面</div>
        </div>
      </>
    );
  }

  const handleSortOrderChange = (channelId: string, value: string) => {
    const numValue = parseInt(value, 10) || 0;
    setEditingSortOrders((prev) => ({ ...prev, [channelId]: numValue }));
    setSavedIds((prev) => {
      const next = new Set(prev);
      next.delete(channelId);
      return next;
    });
  };

  const handleSave = async (channelId: string) => {
    const newSortOrder = editingSortOrders[channelId];
    if (newSortOrder === undefined) return;

    try {
      await updateSortOrderMutation.mutateAsync({ channelId, sortOrder: newSortOrder });
      setSavedIds((prev) => {
        const next = new Set(prev);
        next.add(channelId);
        return next;
      });
    } catch (err) {
      console.error("Update sort order failed:", err);
    }
  };

  return (
    <>
      <Header title="赛道配置" subtitle="配置各赛道的爆款判定参数" />

      <div className="p-6 space-y-6">
        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-bold text-white">赛道列表</h2>
              <p className="text-sm text-dark-textMuted mt-1">
                共 {data.channels.length} 个赛道
              </p>
            </div>
            <button
              onClick={() => refetch()}
              className="btn-secondary flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              刷新
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-dark-border">
                  <th className="text-left py-3 px-4 text-sm font-medium text-dark-textMuted">
                    排序
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-dark-textMuted">
                    赛道名称
                  </th>
                  <th className="text-center py-3 px-4 text-sm font-medium text-dark-textMuted">
                    T_UP (爆款阈值)
                  </th>
                  <th className="text-center py-3 px-4 text-sm font-medium text-dark-textMuted">
                    T_DOWN (衰退阈值)
                  </th>
                  <th className="text-center py-3 px-4 text-sm font-medium text-dark-textMuted">
                    样本数
                  </th>
                  <th className="text-center py-3 px-4 text-sm font-medium text-dark-textMuted">
                    状态
                  </th>
                  <th className="text-center py-3 px-4 text-sm font-medium text-dark-textMuted">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.channels.map((channel) => {
                  const currentSortOrder = editingSortOrders[channel.channel_id ?? ""] ?? channel.sort_order ?? 0;
                  const isModified = editingSortOrders[channel.channel_id ?? ""] !== undefined &&
                    editingSortOrders[channel.channel_id ?? ""] !== (channel.sort_order ?? 0);
                  const isSaved = savedIds.has(channel.channel_id ?? "");

                  return (
                    <tr
                      key={channel.channel_id}
                      className="border-b border-dark-border/50 hover:bg-dark-bg/50"
                    >
                      <td className="py-4 px-4">
                        <input
                          type="number"
                          value={currentSortOrder}
                          onChange={(e) => handleSortOrderChange(channel.channel_id ?? "", e.target.value)}
                          className="w-20 bg-dark-bg border border-dark-border rounded px-2 py-1 text-dark-text text-sm text-center"
                          disabled={channel.status === "inactive"}
                        />
                      </td>
                      <td className="py-4 px-4">
                        <span className="text-white font-medium">
                          {channel.channel_name}
                        </span>
                      </td>
                      <td className="text-center py-4 px-4">
                        <span className="text-dark-text font-mono">
                          {(channel.t_up ?? 0) > 0 ? channel.t_up?.toLocaleString() : "-"}
                        </span>
                      </td>
                      <td className="text-center py-4 px-4">
                        <span className="text-dark-text font-mono">
                          {(channel.t_down ?? 0) > 0 ? channel.t_down?.toLocaleString() : "-"}
                        </span>
                      </td>
                      <td className="text-center py-4 px-4">
                        <span className="text-dark-text">
                          {channel.threshold_sample_count || 0}
                        </span>
                      </td>
                      <td className="text-center py-4 px-4">
                        <div className="flex flex-col items-center gap-1">
                          <span
                            className={clsx(
                              "px-2 py-1 rounded text-xs font-medium",
                              channel.status === "inactive"
                                ? "bg-gray-600/20 text-gray-400"
                                : channel.is_locked
                                ? "bg-red-600/20 text-red-400"
                                : "bg-emerald-600/20 text-emerald-400"
                            )}
                          >
                            {channel.status === "inactive" ? "已失效" : channel.is_locked ? "已锁定" : "正常"}
                          </span>
                        </div>
                      </td>
                      <td className="text-center py-4 px-4">
                        <div className="flex items-center justify-center gap-2">
                          <button
                            onClick={() => handleSave(channel.channel_id ?? "")}
                            disabled={!isModified || channel.status === "inactive" || updateSortOrderMutation.isPending}
                            className={clsx(
                              "p-2 rounded transition-colors",
                              isModified && channel.status !== "inactive"
                                ? "bg-emerald-600/20 text-emerald-400 hover:text-emerald-300 hover:bg-emerald-600/30"
                                : "bg-dark-bg text-dark-textMuted cursor-not-allowed"
                            )}
                            title="保存排序"
                          >
                            <Save className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}