"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Check, Zap, Crown, Sparkles, Loader2, Lock } from "lucide-react";

interface Tier {
  tier: string;
  name: string;
  price: number;
  features: string[];
  limits: {
    day_self_analysis: number;
    month_custom_bvid: number;
    month_compare: number;
  };
}

interface SubscriptionInfo {
  tier?: string;
  valid_until?: string;
  auto_renew?: boolean;
}

export default function MobilePricingPage() {
  const [tiers, setTiers] = useState<Tier[]>([]);
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubscribing, setIsSubscribing] = useState<string | null>(null);
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      // Fetch tiers
      const tiersRes = await fetch("/api/subscribe/tiers");
      if (tiersRes.ok) {
        const tiersData = await tiersRes.json();
        setTiers(tiersData.tiers || []);
      }

      // Fetch subscription status
      const token = localStorage.getItem("bombo_token");
      if (token) {
        const subRes = await fetch("/api/subscribe/my", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (subRes.ok) {
          const subData = await subRes.json();
          setSubscription(subData.subscription);
        }
      }
    } catch (err) {
      console.error("Failed to load data:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubscribe = async (tier: string) => {
    const token = localStorage.getItem("bombo_token");
    if (!token) {
      router.push("/login");
      return;
    }

    setIsSubscribing(tier);
    try {
      // Create order
      const createRes = await fetch("/api/subscribe/create", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ tier, payment_method: "wechat" }),
      });

      if (!createRes.ok) {
        throw new Error("创建订单失败");
      }

      const createData = await createRes.json();

      // Mock payment
      const payRes = await fetch(`/api/subscribe/pay/${createData.order.id}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!payRes.ok) {
        throw new Error("支付失败");
      }

      alert("订阅成功！");
      loadData();
    } catch (err) {
      console.error("Subscription failed:", err);
      alert("订阅失败，请重试");
    } finally {
      setIsSubscribing(null);
    }
  };

  const getTierIcon = (tier: string) => {
    switch (tier) {
      case "light":
        return Zap;
      case "standard":
        return Crown;
      case "pro":
        return Sparkles;
      default:
        return Zap;
    }
  };

  const getTierColor = (tier: string) => {
    switch (tier) {
      case "light":
        return "emerald";
      case "standard":
        return "blue";
      case "pro":
        return "purple";
      default:
        return "gray";
    }
  };

  const isCurrentTier = (tierName: string) => {
    return subscription?.tier === tierName;
  };

  // All tiers including free
  const allTiers = [
    {
      tier: "free",
      name: "免费注册版",
      price: 0,
      features: [
        "浏览全榜单",
        "基础AI分析前32条",
        "无抽帧功能",
        "无自定义视频解析",
      ],
      unavailable: ["抽帧拆解", "自定义视频解析", "对标诊断", "商业化方案"],
    },
    ...tiers,
  ];

  const valueProps = [
    "解锁抽帧拆解，不限次数分析",
    "不限榜单视频AI分析",
    "自定义视频深度诊断",
    "账号商业化规划",
  ];

  return (
    <div className="px-3 py-4 pb-24">
      {/* Value Proposition */}
      <div className="mb-6">
        <h2 className="text-lg font-bold text-gray-800 mb-3">会员权益</h2>
        <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl p-4 text-white">
          <div className="grid grid-cols-2 gap-3">
            {valueProps.map((prop, index) => (
              <div key={index} className="flex items-center gap-2">
                <Check className="w-4 h-4 flex-shrink-0" />
                <span className="text-xs">{prop}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Tier Cards */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
        </div>
      ) : (
        <div className="space-y-4">
          {allTiers.map((tier) => {
            const Icon = getTierIcon(tier.tier);
            const color = getTierColor(tier.tier);
            const current = isCurrentTier(tier.tier);
            const isFree = tier.tier === "free";

            const colorClasses = {
              emerald: {
                border: "border-emerald-300",
                bg: "bg-emerald-50",
                badge: "bg-emerald-500 text-white",
                button: "bg-emerald-600 hover:bg-emerald-700",
              },
              blue: {
                border: "border-blue-300",
                bg: "bg-blue-50",
                badge: "bg-blue-500 text-white",
                button: "bg-blue-600 hover:bg-blue-700",
              },
              purple: {
                border: "border-purple-300",
                bg: "bg-purple-50",
                badge: "bg-purple-500 text-white",
                button: "bg-purple-600 hover:bg-purple-700",
              },
              gray: {
                border: "border-gray-200",
                bg: "bg-gray-50",
                badge: "bg-gray-400 text-white",
                button: "bg-gray-600 hover:bg-gray-700",
              },
            };

            return (
              <div
                key={tier.tier}
                className={`rounded-xl border-2 ${colorClasses[color as keyof typeof colorClasses].border} ${colorClasses[color as keyof typeof colorClasses].bg} p-4`}
              >
                {/* Header */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${current ? "bg-white" : "bg-white/50"}`}>
                      <Icon className={`w-5 h-5 ${current ? "text-blue-600" : "text-gray-600"}`} />
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-800">{tier.name}</h3>
                      {tier.price > 0 && (
                        <span className="text-xs text-gray-500">
                          {tier.tier === "standard" ? "推荐" : tier.tier === "pro" ? "旗舰" : ""}
                        </span>
                      )}
                    </div>
                  </div>
                  {current && (
                    <span className="px-2 py-0.5 bg-green-500 text-white text-xs font-medium rounded-full">
                      已订阅
                    </span>
                  )}
                </div>

                {/* Price */}
                <div className="mb-4">
                  {tier.price > 0 ? (
                    <span className="text-2xl font-bold text-gray-800">
                      ¥{tier.price}
                      <span className="text-sm font-normal text-gray-500">/月</span>
                    </span>
                  ) : (
                    <span className="text-2xl font-bold text-gray-800">免费</span>
                  )}
                </div>

                {/* Features */}
                <div className="space-y-2 mb-4">
                  {tier.features.map((feature, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <Check className="w-4 h-4 text-green-500 flex-shrink-0" />
                      <span className="text-sm text-gray-700">{feature}</span>
                    </div>
                  ))}
                  {tier.unavailable && tier.unavailable.map((feature, index) => (
                    <div key={`unavail-${index}`} className="flex items-center gap-2 opacity-50">
                      <Lock className="w-4 h-4 text-gray-400 flex-shrink-0" />
                      <span className="text-sm text-gray-500 line-through">{feature}</span>
                    </div>
                  ))}
                </div>

                {/* Subscribe Button */}
                {!current && (
                  <button
                    onClick={() => handleSubscribe(tier.tier)}
                    disabled={isSubscribing === tier.tier || isFree}
                    className={`w-full py-2.5 rounded-xl text-sm font-medium text-white transition-colors ${
                      isFree
                        ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                        : isSubscribing === tier.tier
                        ? "bg-gray-400 cursor-not-allowed"
                        : colorClasses[color as keyof typeof colorClasses].button
                    }`}
                  >
                    {isFree ? "免费使用" : isSubscribing === tier.tier ? "处理中..." : "立即开通"}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Footer Note */}
      <div className="mt-6 text-center text-xs text-gray-400">
        <p>• 月付订阅，随时取消</p>
        <p className="mt-1">• 自动续费可随时关闭</p>
      </div>
    </div>
  );
}
