"use client";

import { useState, useEffect } from "react";
import { X, Crown, Zap, Sparkles, ArrowRight } from "lucide-react";
import clsx from "clsx";

interface UpgradePopupProps {
  isOpen: boolean;
  onClose: () => void;
  tier: "tourist" | "free" | "light" | "standard" | "pro";
  targetTier?: "light" | "standard" | "pro";
  trialRemaining?: number;
  onSubscribe?: (tier: string) => void;
}

interface TierInfo {
  tier: string;
  name: string;
  price: number;
  features: string[];
  color: string;
  icon: React.ReactNode;
}

const TIER_CONFIG: Record<string, TierInfo> = {
  light: {
    tier: "light",
    name: "轻量版",
    price: 29,
    features: [
      "每日10次榜单视频自选AI分析",
      "视频抽帧拆解能力",
      "各赛道前40条视频基础分析",
    ],
    color: "emerald",
    icon: <Zap className="w-5 h-5" />,
  },
  standard: {
    tier: "standard",
    name: "标准版",
    price: 89,
    features: [
      "每日10次榜单视频自选AI分析",
      "视频抽帧拆解能力",
      "月度150次自定义BVID分析",
      "月度30次对标诊断",
      "赛道全部视频基础分析",
    ],
    color: "blue",
    icon: <Crown className="w-5 h-5" />,
  },
  pro: {
    tier: "pro",
    name: "专业版",
    price: 299,
    features: [
      "不限次数榜单视频自选AI分析",
      "视频抽帧拆解能力（无限制）",
      "月度500次自定义BVID分析",
      "月度100次对标诊断",
      "专属账号商业化诊断报告",
      "赛道/设备/剪辑软件智能推荐",
    ],
    color: "purple",
    icon: <Sparkles className="w-5 h-5" />,
  },
};

const POPUP_MESSAGES: Record<string, { title: string; description: string; highlight: string }> = {
  trial_exhausted: {
    title: "试用次数已用完",
    description: "登录解锁完整榜单基础分析",
    highlight: "注册即享更多分析额度",
  },
  free_upgrade: {
    title: "解锁视频抽帧拆解",
    description: "升级查看更多AI分析能力",
    highlight: "轻量版仅需29元/月",
  },
  light_upgrade: {
    title: "解锁自定义视频解析",
    description: "标准版支持更多高级功能",
    highlight: "89元/月起",
  },
  standard_upgrade: {
    title: "解锁专属商业化工具",
    description: "专业版全功能无限制",
    highlight: "299元/月",
  },
  pro_upgrade: {
    title: "已是最高版本",
    description: "感谢您的支持",
    highlight: "",
  },
};

export function UpgradePopup({
  isOpen,
  onClose,
  tier,
  targetTier,
  trialRemaining,
  onSubscribe,
}: UpgradePopupProps) {
  const [selectedTier, setSelectedTier] = useState<string>(targetTier || "light");

  useEffect(() => {
    if (targetTier) {
      setSelectedTier(targetTier);
    } else if (tier === "tourist" || tier === "free") {
      setSelectedTier("light");
    } else if (tier === "light") {
      setSelectedTier("standard");
    } else if (tier === "standard") {
      setSelectedTier("pro");
    }
  }, [tier, targetTier]);

  if (!isOpen) return null;

  const messageKey = tier === "tourist" && trialRemaining === 0
    ? "trial_exhausted"
    : tier === "free"
    ? "free_upgrade"
    : tier === "light"
    ? "light_upgrade"
    : tier === "standard"
    ? "standard_upgrade"
    : "pro_upgrade";

  const message = POPUP_MESSAGES[messageKey];

  const getTiersToShow = () => {
    if (tier === "tourist" || tier === "free") {
      return ["light", "standard", "pro"];
    } else if (tier === "light") {
      return ["standard", "pro"];
    } else if (tier === "standard") {
      return ["pro"];
    }
    return [];
  };

  const tiersToShow = getTiersToShow();

  const handleSubscribe = () => {
    if (onSubscribe) {
      onSubscribe(selectedTier);
    }
    // 模拟订阅流程
    console.log(`Subscribing to ${selectedTier}`);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-2xl mx-4 bg-dark-bg rounded-xl shadow-2xl border border-dark-border overflow-hidden">
        {/* Header */}
        <div className="relative p-6 pb-4 bg-gradient-to-r from-yellow-600/20 to-orange-600/20">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-2 rounded-lg hover:bg-white/10 text-dark-textMuted transition"
          >
            <X className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-3 mb-2">
            <Crown className="w-8 h-8 text-yellow-500" />
            <h2 className="text-2xl font-bold text-white">{message.title}</h2>
          </div>
          <p className="text-dark-textMuted">{message.description}</p>
          {message.highlight && (
            <p className="mt-2 text-yellow-400 font-medium">{message.highlight}</p>
          )}

          {tier === "tourist" && trialRemaining !== undefined && (
            <div className="mt-3 inline-flex items-center gap-2 px-3 py-1 bg-yellow-500/20 rounded-full">
              <span className="text-yellow-400 text-sm">剩余试用次数: {trialRemaining}</span>
            </div>
          )}
        </div>

        {/* Tier Selection */}
        {tiersToShow.length > 0 && (
          <div className="p-6 pt-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {tiersToShow.map((tierKey) => {
                const config = TIER_CONFIG[tierKey];
                const isSelected = selectedTier === tierKey;

                return (
                  <button
                    key={tierKey}
                    onClick={() => setSelectedTier(tierKey)}
                    className={clsx(
                      "relative p-4 rounded-xl border-2 transition-all text-left",
                      isSelected
                        ? `border-${config.color}-500 bg-${config.color}-500/10`
                        : "border-dark-border hover:border-dark-border/80 bg-dark-bg"
                    )}
                  >
                    {isSelected && (
                      <div
                        className={clsx(
                          "absolute top-0 right-0 w-6 h-6 rounded-bl-xl rounded-tr-xl flex items-center justify-center",
                          `bg-${config.color}-500`
                        )}
                      >
                        <span className="text-white text-xs">✓</span>
                      </div>
                    )}

                    <div
                      className={clsx(
                        "inline-flex items-center gap-2 px-2 py-1 rounded text-xs font-medium mb-3",
                        config.color === "emerald" && "bg-emerald-500/20 text-emerald-400",
                        config.color === "blue" && "bg-blue-500/20 text-blue-400",
                        config.color === "purple" && "bg-purple-500/20 text-purple-400"
                      )}
                    >
                      {config.icon}
                      {config.name}
                    </div>

                    <div className="mb-3">
                      <span className="text-2xl font-bold text-white">¥{config.price}</span>
                      <span className="text-dark-textMuted">/月</span>
                    </div>

                    <ul className="space-y-1">
                      {config.features.slice(0, 3).map((feature, idx) => (
                        <li
                          key={idx}
                          className="text-xs text-dark-textMuted flex items-start gap-1"
                        >
                          <span className="text-green-400">•</span>
                          {feature}
                        </li>
                      ))}
                      {config.features.length > 3 && (
                        <li className="text-xs text-dark-textMuted">
                          +{config.features.length - 3} 更多权益
                        </li>
                      )}
                    </ul>
                  </button>
                );
              })}
            </div>

            {/* Subscribe Button */}
            <div className="mt-6 flex items-center justify-between">
              <div className="text-sm text-dark-textMuted">
                <span className="text-white font-medium">
                  ¥{TIER_CONFIG[selectedTier]?.price}
                </span>
                /月
                <span className="mx-2">•</span>
                月付订阅
                <span className="mx-2">•</span>
                随时取消
              </div>

              <button
                onClick={handleSubscribe}
                className={clsx(
                  "px-6 py-3 rounded-xl font-medium text-white transition-all flex items-center gap-2",
                  selectedTier === "light" && "bg-emerald-600 hover:bg-emerald-500",
                  selectedTier === "standard" && "bg-blue-600 hover:bg-blue-500",
                  selectedTier === "pro" && "bg-purple-600 hover:bg-purple-500"
                )}
              >
                立即订阅
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Footer */}
        {tiersToShow.length === 0 && (
          <div className="p-6 text-center">
            <p className="text-dark-textMuted">您已是专业版用户，享受全部功能</p>
            <button
              onClick={onClose}
              className="mt-4 px-6 py-2 bg-dark-bg border border-dark-border rounded-lg text-white hover:bg-dark-border/50 transition"
            >
              关闭
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
