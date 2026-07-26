"use client";

import { useState, useEffect } from "react";
import { useAuthStore } from "@/lib/store";
import { Header } from "@/components/Header";
import { User, Shield, Database, Bell, Key, Save, Eye, EyeOff } from "lucide-react";
import clsx from "clsx";

interface SystemConfig {
  key: string;
  value: string;
  description: string;
}

export default function SettingsPage() {
  const { user } = useAuthStore();
  const [configs, setConfigs] = useState<SystemConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  useEffect(() => {
    fetchConfigs();
  }, []);

  const fetchConfigs = async () => {
    try {
      const token = localStorage.getItem("bombo_token");
      const response = await fetch("/api/system-config", {
        headers: {
          Authorization: token || "",
        },
      });
      if (response.ok) {
        const data = await response.json();
        setConfigs(data.configs || []);
      }
    } catch (err) {
      console.error("Failed to fetch configs:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (config: SystemConfig) => {
    setEditingKey(config.key);
    setEditValue(config.value);
  };

  const handleSave = async (key: string) => {
    setSaving(true);
    try {
      const token = localStorage.getItem("bombo_token");
      const response = await fetch("/api/system-config", {
        method: "PUT",
        headers: {
          Authorization: token || "",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ key, value: editValue }),
      });
      if (response.ok) {
        setEditingKey(null);
        fetchConfigs();
      }
    } catch (err) {
      console.error("Failed to save config:", err);
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setEditingKey(null);
    setEditValue("");
  };

  const aiApiKeyConfig = configs.find((c) => c.key === "ai_api_key");

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

        {/* AI API Key */}
        <div className="card p-6">
          <div className="flex items-center gap-3 mb-4">
            <Key className="w-5 h-5 text-primary-400" />
            <h2 className="text-lg font-bold text-white">API 配置</h2>
          </div>
          <div className="bg-dark-bg rounded-lg p-4">
            {loading ? (
              <div className="animate-pulse text-dark-textMuted">加载中...</div>
            ) : aiApiKeyConfig ? (
              <div className="space-y-4">
                <div>
                  <p className="text-dark-textMuted text-sm mb-1">
                    {aiApiKeyConfig.description || "AI API Key"}
                  </p>
                  {editingKey === "ai_api_key" ? (
                    <div className="flex items-center gap-2">
                      <div className="relative flex-1">
                        <input
                          type={showApiKey ? "text" : "password"}
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          className="w-full bg-dark-border border border-dark-border rounded-lg px-4 py-2 pr-10 text-white"
                          placeholder="输入 API Key"
                        />
                        <button
                          type="button"
                          onClick={() => setShowApiKey(!showApiKey)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-dark-textMuted hover:text-white"
                        >
                          {showApiKey ? (
                            <EyeOff className="w-4 h-4" />
                          ) : (
                            <Eye className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                      <button
                        onClick={() => handleSave("ai_api_key")}
                        disabled={saving}
                        className="btn-primary flex items-center gap-2"
                      >
                        <Save className="w-4 h-4" />
                        保存
                      </button>
                      <button
                        onClick={handleCancel}
                        className="btn-secondary"
                      >
                        取消
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-dark-border border border-dark-border rounded-lg px-4 py-2">
                        <span className="text-white font-mono">
                          {aiApiKeyConfig.value
                            ? aiApiKeyConfig.value.slice(0, 8) + "..." + aiApiKeyConfig.value.slice(-4)
                            : "未设置"}
                        </span>
                      </div>
                      <button
                        onClick={() => handleEdit(aiApiKeyConfig)}
                        className="btn-secondary"
                      >
                        编辑
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-dark-textMuted text-sm">AI API Key 配置不存在</p>
            )}
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
              <div className="flex items-center justify-between py-2 border-b border-dark-border/50">
                <span className="text-dark-text">系统配置</span>
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