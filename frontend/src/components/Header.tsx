"use client";

import Link from "next/link";
import { useAuthStore } from "@/lib/store";
import { Bell, Search } from "lucide-react";

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export function Header({ title, subtitle }: HeaderProps) {
  const { user } = useAuthStore();

  return (
    <header className="h-16 bg-dark-card border-b border-dark-border px-6 flex items-center justify-between">
      <div>
        <h1 className="text-xl font-bold text-white">{title}</h1>
        {subtitle && <p className="text-sm text-dark-textMuted">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-4">
        <Link
          href="/search"
          className="p-2 text-dark-textMuted hover:text-white transition"
        >
          <Search className="w-5 h-5" />
        </Link>
        <button className="p-2 text-dark-textMuted hover:text-white transition relative">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
        </button>
        <div className="flex items-center gap-3 pl-4 border-l border-dark-border">
          <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center">
            <span className="text-white text-sm font-medium">
              {user?.username?.charAt(0).toUpperCase() || "U"}
            </span>
          </div>
          <div>
            <p className="text-sm text-white">{user?.username || "用户"}</p>
            <p className="text-xs text-dark-textMuted capitalize">
              {user?.role || "guest"}
            </p>
          </div>
        </div>
      </div>
    </header>
  );
}
