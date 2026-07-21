"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/lib/store";
import {
  LayoutDashboard,
  Video,
  BarChart3,
  Settings,
  LogOut,
  Lock,
  User,
  Crown,
  DollarSign,
} from "lucide-react";
import clsx from "clsx";

const navigation = [
  { name: "控制台", href: "/dashboard", icon: LayoutDashboard },
  { name: "视频管理", href: "/videos", icon: Video },
  { name: "订阅套餐", href: "/pricing", icon: Crown },
  { name: "赛道配置", href: "/channels", icon: BarChart3, permission: "manage_channels" as const },
  { name: "成本统计", href: "/cost", icon: DollarSign, permission: "admin" as const },
  { name: "系统设置", href: "/settings", icon: Settings, permission: "admin" as const },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout, hasPermission } = useAuthStore();

  const filteredNav = navigation.filter((item) => {
    if (!item.permission) return true;
    return hasPermission(item.permission);
  });

  return (
    <aside className="w-64 bg-dark-card border-r border-dark-border flex flex-col h-screen">
      {/* Logo */}
      <div className="p-6 border-b border-dark-border">
        <Link href="/dashboard" className="flex items-center gap-3">
          <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-xl">B</span>
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">BOMBO</h1>
            <p className="text-xs text-dark-textMuted">视频热度监控</p>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {filteredNav.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.name}
              href={item.href}
              className={clsx(
                "flex items-center gap-3 px-4 py-3 rounded-lg transition",
                isActive
                  ? "bg-primary-600/20 text-primary-400"
                  : "text-dark-textMuted hover:bg-dark-border hover:text-white"
              )}
            >
              <item.icon className="w-5 h-5" />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      {/* User Section */}
      <div className="p-4 border-t border-dark-border">
        {user && (
          <div className="mb-3 px-4 py-2">
            <p className="text-sm text-white font-medium">{user.username}</p>
            <p className="text-xs text-dark-textMuted capitalize">
              {user.role === "admin" && "管理员"}
              {user.role === "vip" && "VIP"}
              {user.role === "free" && "免费用户"}
              {user.role === "guest" && "访客"}
            </p>
          </div>
        )}
        <button
          onClick={logout}
          className="flex items-center gap-3 w-full px-4 py-3 text-dark-textMuted hover:text-red-400 hover:bg-dark-border rounded-lg transition"
        >
          <LogOut className="w-5 h-5" />
          <span>退出登录</span>
        </button>
      </div>
    </aside>
  );
}
