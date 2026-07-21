"use client";

import { useChannels, useLockChannel, useUnlockChannel } from "@/hooks/useApi";
import { Header } from "@/components/Header";
import { Lock, Unlock, RefreshCw } from "lucide-react";
import clsx from "clsx";

export default function ChannelsPage() {
  const { data, isLoading, error, refetch } = useChannels();
  const lockMutation = useLockChannel();
  const unlockMutation = useUnlockChannel();

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

  const handleLock = async (channelId: string) => {
    try {
      await lockMutation.mutateAsync(channelId);
      refetch();
    } catch (err) {
      console.error("Lock failed:", err);
    }
  };

  const handleUnlock = async (channelId: string) => {
    try {
      await unlockMutation.mutateAsync(channelId);
      refetch();
    } catch (err) {
      console.error("Unlock failed:", err);
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
                    赛道名称
                  </th>
                  <th className="text-center py-3 px-4 text-sm font-medium text-dark-textMuted">
                    爆款增速阈值
                  </th>
                  <th className="text-center py-3 px-4 text-sm font-medium text-dark-textMuted">
                    爆款容量阈值
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
                {data.channels.map((channel) => (
                  <tr
                    key={channel.channel_id}
                    className="border-b border-dark-border/50 hover:bg-dark-bg/50"
                  >
                    <td className="py-4 px-4">
                      <span className="text-white font-medium">
                        {channel.channel_name}
                      </span>
                    </td>
                    <td className="text-center py-4 px-4">
                      <span className="text-dark-text">
                        {channel.burst_growth_threshold}%
                      </span>
                    </td>
                    <td className="text-center py-4 px-4">
                      <span className="text-dark-text">
                        {channel.burst_volume_threshold.toLocaleString()}
                      </span>
                    </td>
                    <td className="text-center py-4 px-4">
                      <span
                        className={clsx(
                          "px-2 py-1 rounded text-xs font-medium",
                          channel.is_locked
                            ? "bg-red-600/20 text-red-400"
                            : "bg-emerald-600/20 text-emerald-400"
                        )}
                      >
                        {channel.is_locked ? "已锁定" : "正常"}
                      </span>
                    </td>
                    <td className="text-center py-4 px-4">
                      <div className="flex items-center justify-center gap-2">
                        {channel.is_locked ? (
                          <button
                            onClick={() => handleUnlock(channel.channel_id)}
                            disabled={unlockMutation.isPending}
                            className="p-2 hover:bg-dark-bg rounded text-emerald-400 hover:text-emerald-300"
                            title="解锁赛道"
                          >
                            <Unlock className="w-4 h-4" />
                          </button>
                        ) : (
                          <button
                            onClick={() => handleLock(channel.channel_id)}
                            disabled={lockMutation.isPending}
                            className="p-2 hover:bg-dark-bg rounded text-red-400 hover:text-red-300"
                            title="锁定赛道"
                          >
                            <Lock className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}
