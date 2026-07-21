"use client";

import { useState, useEffect } from "react";
import { Check, Crown, Zap, Sparkles, ArrowRight, CreditCard } from "lucide-react";
import clsx from "clsx";
import { Header } from "@/components/Header";
import { useRouter } from "next/navigation";

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
  order_id?: number;
  tier?: string;
  valid_until?: string;
  auto_renew?: boolean;
}

export default function PricingPage() {
  const router = useRouter();
  const [tiers, setTiers] = useState<Tier[]>([]);
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedTier, setSelectedTier] = useState<string | null>(null);
  const [isSubscribing, setIsSubscribing] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      // 获取套餐列表
      const tiersRes = await fetch("/api/subscribe/tiers");
      if (tiersRes.ok) {
        const tiersData = await tiersRes.json();
        setTiers(tiersData.tiers || []);
      }

      // 获取当前订阅状态
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
    } catch (error) {
      console.error("Failed to load subscription data:", error);
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

    setIsSubscribing(true);
    try {
      // 创建订单
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

      // 模拟支付
      const payRes = await fetch(`/api/subscribe/pay/${createData.order.id}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!payRes.ok) {
        throw new Error("支付失败");
      }

      alert("订阅成功！");
      loadData(); // 刷新数据
    } catch (error) {
      console.error("Subscription failed:", error);
      alert("订阅失败，请重试");
    } finally {
      setIsSubscribing(false);
    }
  };

  const getTierIcon = (tier: string) => {
    switch (tier) {
      case "light":
        return <Zap className="w-6 h-6" />;
      case "standard":
        return <Crown className="w-6 h-6" />;
      case "pro":
        return <Sparkles className="w-6 h-6" />;
      default:
        return <Zap className="w-6 h-6" />;
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
        return "emerald";
    }
  };

  const isCurrentTier = (tierName: string) => {
    return subscription?.tier === tierName;
  };

  return (
    <>
      <Header title="订阅套餐" subtitle="解锁更多高级功能" />

      <div className="p-6 max-w-6xl mx-auto">
        {/* Current Subscription Status */}
        {subscription && (
          <div className="mb-8 p-4 bg-dark-bg rounded-xl border border-dark-border">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-dark-textMuted text-sm">当前订阅</p>
                <p className="text-white font-medium">
                  {subscription.tier
                    ? `${subscription.tier}版`
                    : "免费用户"}
                </p>
                {subscription.valid_until && (
                  <p className="text-dark-textMuted text-sm mt-1">
                    到期时间: {new Date(subscription.valid_until).toLocaleDateString()}
                  </p>
                )}
              </div>
              {subscription.auto_renew && (
                <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-sm">
                  自动续费开启
                </span>
              )}
            </div>
          </div>
        )}

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {tiers.map((tier) => {
            const color = getTierColor(tier.tier);
            const isCurrent = isCurrentTier(tier.tier);
            const isRecommended = tier.tier === "standard";

            return (
              <div
                key={tier.tier}
                className={clsx(
                  "relative rounded-2xl border transition-all",
                  isCurrent
                    ? "border-green-500 bg-green-500/5"
                    : isRecommended
                    ? `border-${color}-500 bg-${color}-500/5`
                    : "border-dark-border bg-dark-bg hover:border-dark-border/80"
                )}
              >
                {isRecommended && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-blue-500 text-white text-xs font-medium rounded-full">
                    推荐
                  </div>
                )}

                {isCurrent && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-green-500 text-white text-xs font-medium rounded-full">
                    当前
                  </div>
                )}

                <div className="p-6">
                  {/* Tier Header */}
                  <div
                    className={clsx(
                      "inline-flex items-center gap-2 px-3 py-1 rounded-lg text-sm font-medium mb-4",
                      color === "emerald" && "bg-emerald-500/20 text-emerald-400",
                      color === "blue" && "bg-blue-500/20 text-blue-400",
                      color === "purple" && "bg-purple-500/20 text-purple-400"
                    )}
                  >
                    {getTierIcon(tier.tier)}
                    {tier.name}
                  </div>

                  {/* Price */}
                  <div className="mb-6">
                    <span className="text-4xl font-bold text-white">
                      ¥{tier.price}
                    </span>
                    <span className="text-dark-textMuted">/月</span>
                  </div>

                  {/* Features */}
                  <ul className="space-y-3 mb-6">
                    {tier.features.map((feature, idx) => (
                      <li
                        key={idx}
                        className="flex items-start gap-2 text-sm"
                      >
                        <Check className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                        <span className="text-dark-textMuted">{feature}</span>
                      </li>
                    ))}
                  </ul>

                  {/* Limits */}
                  <div className="mb-6 p-3 bg-dark-bg rounded-lg">
                    <p className="text-xs text-dark-textMuted mb-2">额度限制</p>
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div>
                        <p className="text-white font-medium">
                          {tier.limits.day_self_analysis === 999999
                            ? "∞"
                            : tier.limits.day_self_analysis}
                        </p>
                        <p className="text-dark-textMuted">每日自选</p>
                      </div>
                      <div>
                        <p className="text-white font-medium">
                          {tier.limits.month_custom_bvid}
                        </p>
                        <p className="text-dark-textMuted">月度自定义</p>
                      </div>
                      <div>
                        <p className="text-white font-medium">
                          {tier.limits.month_compare}
                        </p>
                        <p className="text-dark-textMuted">月度对标</p>
                      </div>
                    </div>
                  </div>

                  {/* Subscribe Button */}
                  <button
                    onClick={() => handleSubscribe(tier.tier)}
                    disabled={isCurrent || isSubscribing}
                    className={clsx(
                      "w-full py-3 rounded-xl font-medium transition-all flex items-center justify-center gap-2",
                      isCurrent
                        ? "bg-green-500/20 text-green-400 cursor-not-allowed"
                        : color === "emerald"
                        ? "bg-emerald-600 hover:bg-emerald-500 text-white"
                        : color === "blue"
                        ? "bg-blue-600 hover:bg-blue-500 text-white"
                        : "bg-purple-600 hover:bg-purple-500 text-white"
                    )}
                  >
                    {isCurrent ? (
                      <>
                        <Check className="w-4 h-4" />
                        当前版本
                      </>
                    ) : isSubscribing ? (
                      "处理中..."
                    ) : (
                      <>
                        <CreditCard className="w-4 h-4" />
                        立即订阅
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer Note */}
        <div className="mt-8 text-center text-sm text-dark-textMuted">
          <p>• 月付订阅，随时取消 • 自动续费可随时关闭</p>
          <p className="mt-1">如有疑问请联系客服</p>
        </div>
      </div>
    </>
  );
}
