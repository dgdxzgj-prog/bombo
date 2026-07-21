"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { MobileTabBar } from "@/components/MobileTabBar";
import { User, Crown } from "lucide-react";

interface UserStatus {
  user_level: string;
  is_login: boolean;
  permissions: {
    user_level: string;
    is_paid: boolean;
    tier: string | null;
    status_label: string;
    trial_count?: number;
  };
  quotas: {
    day_self_analysis?: { remaining: number; total: number };
    month_custom_bvid?: { remaining: number; total: number };
    month_compare?: { remaining: number; total: number };
  };
}

export default function MobileLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [userStatus, setUserStatus] = useState<UserStatus | null>(null);
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
        setUserStatus(data);
      }
    } catch (err) {
      console.error("Failed to fetch user status:", err);
    }
  };

  const handleLogin = () => {
    router.push("/login");
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

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 bg-white border-b border-gray-200 z-40 safe-area-top">
        <div className="flex items-center justify-between px-4 h-14 max-w-lg mx-auto">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">B</span>
            </div>
            <span className="font-bold text-gray-800">Bombo爆款雷达</span>
          </div>

          <div className="flex items-center gap-3">
            {userStatus?.is_login ? (
              <div className="flex items-center gap-2">
                <span
                  className={`px-2 py-0.5 rounded text-xs font-medium ${getUserLevelBadgeColor(
                    userStatus.permissions?.tier || "free"
                  )}`}
                >
                  {userStatus.permissions?.status_label || "免费用户"}
                </span>
                <div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center">
                  <User className="w-4 h-4 text-gray-600" />
                </div>
              </div>
            ) : (
              <button
                onClick={handleLogin}
                className="flex items-center gap-1 text-blue-600 text-sm font-medium"
              >
                <span>登录</span>
                <Crown className="w-3.5 h-3.5 text-yellow-500" />
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 pt-14 pb-16 overflow-y-auto">
        <div className="max-w-lg mx-auto">{children}</div>
      </main>

      {/* Bottom Tab Bar */}
      <MobileTabBar />
    </div>
  );
}
