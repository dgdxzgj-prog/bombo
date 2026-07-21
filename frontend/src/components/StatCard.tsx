"use client";

import { LucideIcon } from "lucide-react";
import clsx from "clsx";

interface StatCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  icon: LucideIcon;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  className?: string;
}

export function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  className,
}: StatCardProps) {
  return (
    <div className={clsx("card p-6", className)}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-dark-textMuted">{title}</p>
          <p className="text-3xl font-bold text-white mt-2">{value}</p>
          {subtitle && (
            <p className="text-sm text-dark-textMuted mt-1">{subtitle}</p>
          )}
          {trend && (
            <p
              className={clsx(
                "text-sm mt-2",
                trend.isPositive ? "text-emerald-400" : "text-red-400"
              )}
            >
              {trend.isPositive ? "↑" : "↓"} {Math.abs(trend.value)}%
            </p>
          )}
        </div>
        <div className="p-3 bg-primary-600/20 rounded-lg">
          <Icon className="w-6 h-6 text-primary-400" />
        </div>
      </div>
    </div>
  );
}
