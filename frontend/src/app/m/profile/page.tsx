"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { User, Zap, Users, Crown, History, Settings, Bell, ChevronRight, LogOut } from "lucide-react";

interface UserStatus {
  user_level: string;
  is_login: boolean;
  permissions: {
    user_level: string;
    is_paid: boolean;
    tier: string | null;
    status_label: string;
    subscribe_expire?: string;
  };
  quotas: {
    day_self_analysis?: { remaining: number; total: number };
    month_custom_bvid?: { remaining: number; total: number };
    month_compare?: { remaining: number; total: number };
  };
}

export default function MobileProfilePage() {
  const [userStatus, setUserStatus] = useState<UserStatus | null>(null);
  const router = useRouter();

  useEffect(() => {
    fetchUserStatus();
  }, []);

  const fetchUserStatus = async () => {
    try {
      const res = await fetch("/api/videos/user-status");
      if (res.ok) {
        const data = await res.json();
        setUserStatus(data);
      }
    } catch (err) {
      console.error("Failed to fetch user status:", err);
    }
  };

  const handleLogin = () => {
    router.push("/login");
  };

  const handleLogout = () => {
    localStorage.removeItem("bombo_token");
    localStorage.removeItem("bombo_user");
    window.location.reload();
  };

  const handleUpgrade = () => {
    router.push("/m/pricing");
  };

  const getUserLevelBadgeColor = (level: string) => {
    switch (level) {
      case "pro":
        return "bg-purple-500 text-white";
      case "standard":
        return "bg-blue-500 text-white";
      case "light":
        return "bg-emerald-500 text-white";
      case "free":
        return "bg-gray-500 text-white";
      default:
        return "bg-gray-300 text-gray-600";
    }
  };

  const menuItems = [
    { icon: History, label: "历史分析记录", href: "/m/analysis" },
    { icon: Crown, label: "采集监控池", href: "/m" },
    { icon: Bell, label: "消息通知", href: "#" },
    { icon: Settings, label: "设置", href: "/settings" },
  ];

  return (
    <div className="px-3 py-4">
      {/* User Info Card */}
      <div className="bg-white rounded-xl p-4 shadow-sm mb-4">
        {userStatus?.is_login ? (
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-gray-200 rounded-full flex items-center justify-center">
              <User className="w-7 h-7 text-gray-400" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-medium text-gray-800">
                  {userStatus.permissions?.status_label || "用户"}
                </span>
                {userStatus.permissions?.tier && (
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${getUserLevelBadgeColor(
                      userStatus.permissions.tier
                    )}`}
                  >
                    {userStatus.permissions.status_label}
                  </span>
                )}
              </div>
              {userStatus.permissions?.subscribe_expire && (
                <p className="text-xs text-gray-500">
                  到期时间：{new Date(userStatus.permissions.subscribe_expire).toLocaleDateString()}
                </p>
              )}
            </div>
          </div>
        ) : (
          <div className="text-center py-4">
            <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mx-auto mb-3">
              <User className="w-8 h-8 text-gray-400" />
            </div>
            <p className="text-gray-500 text-sm mb-3">游客身份</p>
            <p className="text-gray-400 text-xs mb-4">登录解锁完整能力</p>
            <button
              onClick={handleLogin}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
            >
              登录 / 注册
            </button>
          </div>
        )}
      </div>

      {/* Quota Cards - only for logged in users */}
      {userStatus?.is_login && userStatus.quotas && (
        <div className="mb-4">
          <h3 className="text-sm font-medium text-gray-600 mb-3">额度统计</h3>
          <div className="grid grid-cols-3 gap-2">
            <QuotaCard
              title="今日自选"
              remaining={userStatus.quotas.day_self_analysis?.remaining || 0}
              total={userStatus.quotas.day_self_analysis?.total || 0}
              color="blue"
            />
            <QuotaCard
              title="月度自定义"
              remaining={userStatus.quotas.month_custom_bvid?.remaining || 0}
              total={userStatus.quotas.month_custom_bvid?.total || 0}
              color="emerald"
              locked={!["standard", "pro"].includes(userStatus.user_level)}
            />
            <QuotaCard
              title="对标诊断"
              remaining={userStatus.quotas.month_compare?.remaining || 0}
              total={userStatus.quotas.month_compare?.total || 0}
              color="purple"
              locked={!["standard", "pro"].includes(userStatus.user_level)}
            />
          </div>
        </div>
      )}

      {/* Menu Items */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden mb-4">
        {menuItems.map((item, index) => (
          <button
            key={item.label}
            onClick={() => item.href !== "#" && router.push(item.href)}
            className={`w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors ${
              index < menuItems.length - 1 ? "border-b border-gray-100" : ""
            }`}
          >
            <div className="flex items-center gap-3">
              <item.icon className="w-5 h-5 text-gray-400" />
              <span className="text-sm text-gray-800">{item.label}</span>
            </div>
            <ChevronRight className="w-4 h-4 text-gray-400" />
          </button>
        ))}
      </div>

      {/* Logout Button - only for logged in users */}
      {userStatus?.is_login && (
        <button
          onClick={handleLogout}
          className="w-full flex items-center justify-center gap-2 py-3 bg-gray-100 text-gray-600 rounded-xl text-sm font-medium hover:bg-gray-200"
        >
          <LogOut className="w-4 h-4" />
          退出登录
        </button>
      )}

      {/* Upgrade Floating Button */}
      {userStatus?.is_login && !["pro"].includes(userStatus.user_level || "") && (
        <button
          onClick={handleUpgrade}
          className="fixed bottom-20 left-4 right-4 max-w-lg mx-auto py-3 bg-orange-500 text-white rounded-full text-sm font-medium shadow-lg hover:bg-orange-600 transition-colors"
        >
          升级会员，解锁更多权益
        </button>
      )}
    </div>
  );
}

interface QuotaCardProps {
  title: string;
  remaining: number;
  total: number;
  color: string;
  locked?: boolean;
}

function QuotaCard({ title, remaining, total, color, locked }: QuotaCardProps) {
  const colorClasses = {
    blue: "bg-blue-50 text-blue-600",
    emerald: "bg-emerald-50 text-emerald-600",
    purple: "bg-purple-50 text-purple-600",
    orange: "bg-orange-50 text-orange-600",
  };

  return (
    <div className={`rounded-xl p-3 ${locked ? "bg-gray-100" : colorClasses[color as keyof typeof colorClasses]}`}>
      <p className="text-xs font-medium mb-1">{title}</p>
      {locked ? (
        <p className="text-xs text-gray-400">不可用</p>
      ) : (
        <p className="text-lg font-bold">
          {remaining}
          <span className="text-xs font-normal text-gray-500">/{total}</span>
        </p>
      )}
    </div>
  );
}
