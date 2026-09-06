"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Bookmark, CreditCard, User } from "lucide-react";
import clsx from "clsx";

const tabs = [
  { name: "榜单", href: "/m", icon: Home, disabled: false },
  { name: "自选赛道", href: "/m/my-feed", icon: Bookmark, disabled: false },
  { name: "会员", href: "/m/pricing", icon: CreditCard, disabled: true },
  { name: "我的", href: "/m/profile", icon: User, disabled: false },
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
          const disabled = tab.disabled;

          if (disabled) {
            return (
              <span
                key={tab.name}
                className="flex flex-col items-center justify-center w-full h-full text-gray-400 cursor-not-allowed"
              >
                <tab.icon className="w-5 h-5 text-gray-400" />
                <span className="text-xs mt-0.5 text-gray-400">
                  {tab.name}
                </span>
              </span>
            );
          }

          return (
            <Link
              key={tab.name}
              href={tab.href}
              className={clsx(
                "flex flex-col items-center justify-center w-full h-full transition-colors",
                active ? "text-violet-600" : "text-gray-400 hover:text-gray-600"
              )}
            >
              <tab.icon className={clsx("w-5 h-5", active && "text-violet-600")} />
              <span className={clsx("text-xs mt-0.5", active && "font-medium text-violet-600")}>
                {tab.name}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
