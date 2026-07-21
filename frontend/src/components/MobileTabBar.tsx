"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Bookmark, CreditCard, User } from "lucide-react";
import clsx from "clsx";

const tabs = [
  { name: "榜单", href: "/m", icon: Home },
  { name: "自选赛道", href: "/m/analysis", icon: Bookmark },
  { name: "会员", href: "/m/pricing", icon: CreditCard },
  { name: "我的", href: "/m/profile", icon: User },
];

export function MobileTabBar() {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/m") {
      return pathname === "/m" || pathname === "/m/";
    }
    return pathname.startsWith(href);
  };

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-50 safe-area-bottom">
      <div className="flex justify-around items-center h-14 max-w-lg mx-auto">
        {tabs.map((tab) => {
          const active = isActive(tab.href);
          return (
            <Link
              key={tab.name}
              href={tab.href}
              className={clsx(
                "flex flex-col items-center justify-center w-full h-full transition-colors",
                active ? "text-blue-600" : "text-gray-400 hover:text-gray-600"
              )}
            >
              <tab.icon className={clsx("w-5 h-5", active && "text-blue-600")} />
              <span className={clsx("text-xs mt-0.5", active && "font-medium")}>
                {tab.name}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
