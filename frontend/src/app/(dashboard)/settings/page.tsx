"use client";

import { useAuthStore } from "@/lib/store";
import { Header } from "@/components/Header";
import { User, Shield, Database, Bell } from "lucide-react";

export default function SettingsPage() {
  const { user } = useAuthStore();

  return (
    <>
      <Header title="系统设置" subtitle="系统配置和用户管理" />

      <div className="p-6 space-y-6">
        {/* User Info */}
        <div className="card p-6">
          <div className="flex items-center gap-3 mb-4">
            <User className="w-5 h-5 text-primary-400" />
            <h2 className="text-lg font-bold text-white">当前用户</h2>
          </div>
          <div className="bg-dark-bg rounded-lg p-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-dark-textMuted text-sm">用户名</p>
                <p className="text-white font-medium">{user?.username}</p>
              </div>
              <div>
                <p className="text-dark-textMuted text-sm">角色</p>
                <p className="text-white font-medium">
                  {user?.role === "admin" && "管理员"}
                  {user?.role === "vip" && "VIP用户"}
                  {user?.role === "free" && "免费用户"}
                  {user?.role === "guest" && "访客"}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* System Info */}
        <div className="card p-6">
          <div className="flex items-center gap-3 mb-4">
            <Database className="w-5 h-5 text-primary-400" />
            <h2 className="text-lg font-bold text-white">系统信息</h2>
          </div>
          <div className="bg-dark-bg rounded-lg p-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-dark-textMuted text-sm">版本</p>
                <p className="text-white font-medium">BOMBO V1.0</p>
              </div>
              <div>
                <p className="text-dark-textMuted text-sm">数据库</p>
                <p className="text-white font-medium">PostgreSQL</p>
              </div>
              <div>
                <p className="text-dark-textMuted text-sm">B站API</p>
                <p className="text-white font-medium">bilibili-api v8.3.1</p>
              </div>
              <div>
                <p className="text-dark-textMuted text-sm">前端框架</p>
                <p className="text-white font-medium">Next.js 15.5.20</p>
              </div>
            </div>
          </div>
        </div>

        {/* Permissions */}
        <div className="card p-6">
          <div className="flex items-center gap-3 mb-4">
            <Shield className="w-5 h-5 text-primary-400" />
            <h2 className="text-lg font-bold text-white">权限说明</h2>
          </div>
          <div className="bg-dark-bg rounded-lg p-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between py-2 border-b border-dark-border/50">
                <span className="text-dark-text">查看视频</span>
                <span className="text-xs px-2 py-1 bg-blue-600/20 text-blue-400 rounded">
                  所有用户
                </span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-dark-border/50">
                <span className="text-dark-text">AI分析</span>
                <span className="text-xs px-2 py-1 bg-emerald-600/20 text-emerald-400 rounded">
                  VIP
                </span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-dark-border/50">
                <span className="text-dark-text">赛道管理</span>
                <span className="text-xs px-2 py-1 bg-red-600/20 text-red-400 rounded">
                  管理员
                </span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-dark-text">用户管理</span>
                <span className="text-xs px-2 py-1 bg-red-600/20 text-red-400 rounded">
                  管理员
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Notifications */}
        <div className="card p-6">
          <div className="flex items-center gap-3 mb-4">
            <Bell className="w-5 h-5 text-primary-400" />
            <h2 className="text-lg font-bold text-white">通知设置</h2>
          </div>
          <div className="bg-dark-bg rounded-lg p-4">
            <p className="text-dark-textMuted text-sm">
              通知功能正在开发中，敬请期待...
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
