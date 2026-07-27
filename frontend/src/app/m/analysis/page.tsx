"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Plus, Edit, Trash2, X, Check, Eye } from "lucide-react";

interface CustomChannel {
  id: number;
  user_id: number;
  channel_name: string;
  keywords: string;
  created_at: string;
}

interface UserStatus {
  user_level: string;
  is_login: boolean;
  username?: string;
}

export default function MobileAnalysisPage() {
  const [userStatus, setUserStatus] = useState<UserStatus | null>(null);
  const [customChannels, setCustomChannels] = useState<CustomChannel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showEditModal, setShowEditModal] = useState(false);
  const [newChannelName, setNewChannelName] = useState("");
  const [newKeywords, setNewKeywords] = useState("");
  const [editingChannel, setEditingChannel] = useState<CustomChannel | null>(null);
  const router = useRouter();

  useEffect(() => {
    fetchUserStatus();
  }, []);

  const fetchUserStatus = async () => {
    try {
      const token = localStorage.getItem("bombo_token");
      const headers: HeadersInit = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      const res = await fetch("/api/videos/user-status", { headers });
      if (res.ok) {
        const data = await res.json();
        setUserStatus({
          is_login: data.is_login,
          user_level: data.user_level,
          username: data.username,
        });
        if (data.is_login) {
          fetchCustomChannels();
        }
      }
    } catch (err) {
      console.error("Failed to fetch user status:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchCustomChannels = async () => {
    try {
      const token = localStorage.getItem("bombo_token");
      const res = await fetch("/api/channels/custom-channels", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setCustomChannels(data.channels || []);
      }
    } catch (err) {
      console.error("Failed to fetch custom channels:", err);
    }
  };

  const addCustomChannel = async () => {
    if (!newChannelName.trim() || !newKeywords.trim()) return;
    try {
      const token = localStorage.getItem("bombo_token");
      const res = await fetch("/api/channels/custom-channels", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ channel_name: newChannelName.trim(), keywords: newKeywords.trim() }),
      });
      if (res.ok) {
        setNewChannelName("");
        setNewKeywords("");
        fetchCustomChannels();
      }
    } catch (err) {
      console.error("Failed to add custom channel:", err);
    }
  };

  const updateCustomChannel = async () => {
    if (!editingChannel || !newChannelName.trim() || !newKeywords.trim()) return;
    try {
      const token = localStorage.getItem("bombo_token");
      const res = await fetch(`/api/channels/custom-channels/${editingChannel.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ channel_name: newChannelName.trim(), keywords: newKeywords.trim() }),
      });
      if (res.ok) {
        setEditingChannel(null);
        setNewChannelName("");
        setNewKeywords("");
        fetchCustomChannels();
      }
    } catch (err) {
      console.error("Failed to update custom channel:", err);
    }
  };

  const deleteCustomChannel = async (id: number) => {
    try {
      const token = localStorage.getItem("bombo_token");
      const res = await fetch(`/api/channels/custom-channels/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        if (editingChannel?.id === id) {
          setEditingChannel(null);
          setNewChannelName("");
          setNewKeywords("");
        }
        fetchCustomChannels();
      }
    } catch (err) {
      console.error("Failed to delete custom channel:", err);
    }
  };

  const openEditModal = (channel?: CustomChannel) => {
    if (channel) {
      setEditingChannel(channel);
      setNewChannelName(channel.channel_name);
      setNewKeywords(channel.keywords);
    } else {
      setEditingChannel(null);
      setNewChannelName("");
      setNewKeywords("");
    }
    setShowEditModal(true);
  };

  const closeModal = () => {
    setShowEditModal(false);
    setEditingChannel(null);
    setNewChannelName("");
    setNewKeywords("");
  };

  // Redirect tourists to login
  if (!isLoading && !userStatus?.is_login) {
    return (
      <div className="min-h-screen bg-[#f4f5f7] flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mx-auto mb-4">
            <Edit className="w-8 h-8 text-gray-400" />
          </div>
          <p className="text-gray-500 mb-4">登录后解锁自选赛道功能</p>
          <button
            onClick={() => router.push("/login")}
            className="px-6 py-2 bg-violet-600 text-white rounded-lg text-sm font-medium"
          >
            登录 / 注册
          </button>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#f4f5f7] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-violet-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="bg-[#f4f5f7] min-h-screen pb-20">
      {/* Top Header */}
      <header className="bg-violet-600 text-white safe-area-top">
        <div className="max-w-lg mx-auto">
          <div className="flex items-center justify-between px-3 py-2">
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold tracking-tight">BOMBO</span>
              <span className="text-xs bg-violet-500 px-1.5 py-0.5 rounded">自选赛道</span>
            </div>
            <div className="flex items-center gap-2">
              {userStatus?.is_login ? (
                <div className="flex items-center gap-1.5">
                  <div className="w-7 h-7 rounded-full bg-violet-400 flex items-center justify-center text-sm font-medium">
                    {userStatus.username?.[0]?.toUpperCase() || "U"}
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => router.push("/login")}
                  className="w-8 h-8 rounded-full bg-violet-500 hover:bg-violet-400 text-white text-xs font-medium transition-colors flex items-center justify-center"
                >
                  登录
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Channel Tags */}
      <div className="px-2 py-2 bg-white border-b border-gray-100">
        <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
          <button
            onClick={() => openEditModal()}
            className="flex-shrink-0 px-3 py-1 bg-violet-600 text-white rounded-full text-xs font-medium flex items-center gap-1"
          >
            <Edit className="w-3 h-3" />
            编辑
          </button>
          {customChannels.map((cc) => (
            <button
              key={cc.id}
              onClick={() => openEditModal(cc)}
              className="flex-shrink-0 px-2 py-1 bg-gray-100 text-gray-600 hover:bg-gray-200 rounded-full text-xs font-medium"
            >
              {cc.channel_name}
            </button>
          ))}
        </div>
      </div>

      {/* Empty State */}
      {customChannels.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
            <Eye className="w-8 h-8 text-gray-400" />
          </div>
          <p className="text-gray-500 text-sm mb-2">暂无自定义赛道</p>
          <p className="text-gray-400 text-xs mb-4 text-center px-4">点击上方"编辑"按钮创建自定义赛道</p>
          <button
            onClick={() => openEditModal()}
            className="px-4 py-2 bg-violet-600 text-white rounded-lg text-sm font-medium flex items-center gap-1"
          >
            <Plus className="w-4 h-4" />
            创建赛道
          </button>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-sm rounded-xl overflow-hidden max-h-[80vh] flex flex-col">
            <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between flex-shrink-0">
              <h3 className="font-medium text-gray-800">
                {editingChannel ? "编辑赛道" : "创建赛道"}
              </h3>
              <button onClick={closeModal} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Form */}
            <div className="p-4 space-y-4 flex-shrink-0">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">赛道名称</label>
                <input
                  type="text"
                  value={newChannelName}
                  onChange={(e) => setNewChannelName(e.target.value)}
                  placeholder="例如：数码科技"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">搜索关键词</label>
                <textarea
                  value={newKeywords}
                  onChange={(e) => setNewKeywords(e.target.value)}
                  placeholder="多个关键词用逗号分隔，例如：手机,电脑,数码"
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-violet-500 resize-none"
                />
                <p className="text-xs text-gray-400 mt-1">多个关键词用逗号分隔</p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    if (editingChannel) {
                      updateCustomChannel();
                    } else {
                      addCustomChannel();
                    }
                  }}
                  disabled={!newChannelName.trim() || !newKeywords.trim()}
                  className="flex-1 py-2 bg-violet-600 text-white rounded-lg text-sm font-medium flex items-center justify-center gap-1 disabled:opacity-50"
                >
                  <Check className="w-4 h-4" />
                  {editingChannel ? "保存" : "创建"}
                </button>
              </div>
            </div>

            {/* Channel List */}
            {customChannels.length > 0 && (
              <div className="flex-1 overflow-y-auto border-t border-gray-100">
                <div className="p-4">
                  <p className="text-xs text-gray-500 mb-2">已创建 ({customChannels.length})</p>
                  <div className="space-y-2">
                    {customChannels.map((cc) => (
                      <div
                        key={cc.id}
                        className={`flex items-center justify-between p-3 rounded-lg border ${
                          editingChannel?.id === cc.id ? "border-violet-300 bg-violet-50" : "border-gray-100 bg-gray-50"
                        }`}
                      >
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-800 truncate">{cc.channel_name}</p>
                          <p className="text-xs text-gray-400 truncate">{cc.keywords}</p>
                        </div>
                        <div className="flex items-center gap-1 ml-2">
                          <button
                            onClick={() => openEditModal(cc)}
                            className="p-1.5 text-gray-400 hover:text-violet-600"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => deleteCustomChannel(cc.id)}
                            className="p-1.5 text-gray-400 hover:text-red-600"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
