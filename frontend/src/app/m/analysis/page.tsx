"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Search, Loader2, Lock, Zap, Users, Crown } from "lucide-react";

interface UserStatus {
  user_level: string;
  is_login: boolean;
  permissions: {
    user_level: string;
    is_paid: boolean;
    tier: string | null;
    status_label: string;
    upgrade_hint?: string;
    upgrade_tiers?: Array<{ tier: string; price: number }>;
  };
  quotas: {
    day_self_analysis?: { remaining: number; total: number };
    month_custom_bvid?: { remaining: number; total: number };
    month_compare?: { remaining: number; total: number };
  };
}

export default function MobileAnalysisPage() {
  const [userStatus, setUserStatus] = useState<UserStatus | null>(null);
  const [bvid, setBvid] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    fetchUserStatus();
    // Check if bvid is passed in URL
    const urlBvid = searchParams.get("bvid");
    if (urlBvid) {
      setBvid(urlBvid);
      handleAnalyze(urlBvid);
    }
  }, [searchParams]);

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

  const handleAnalyze = async (targetBvid?: string) => {
    const inputBvid = targetBvid || bvid.trim();
    if (!inputBvid) return;

    // Check permission for custom BVID analysis
    const canCustomAnalysis =
      userStatus?.user_level === "standard" || userStatus?.user_level === "pro";

    if (!canCustomAnalysis) {
      alert("自定义视频解析仅标准版和专业版可用，升级后解锁");
      return;
    }

    // Check quota
    if (userStatus?.quotas?.month_custom_bvid) {
      if (userStatus.quotas.month_custom_bvid.remaining <= 0) {
        alert("月度自定义分析额度已用完，请升级提升额度");
        return;
      }
    }

    setIsLoading(true);
    try {
      const res = await fetch(`/api/videos/${inputBvid}`);
      if (res.ok) {
        const data = await res.json();
        setAnalysisResult(data.ai_analysis);
      } else {
        alert("视频不存在或获取分析失败");
      }
    } catch (err) {
      console.error("Analysis failed:", err);
      alert("分析失败，请重试");
    } finally {
      setIsLoading(false);
    }
  };

  const canUseFeature = (feature: string) => {
    const level = userStatus?.user_level;
    switch (feature) {
      case "self_analysis":
        return ["light", "standard", "pro"].includes(level || "");
      case "custom_bvid":
        return ["standard", "pro"].includes(level || "");
      case "compare":
        return ["standard", "pro"].includes(level || "");
      case "commercial":
        return level === "pro";
      default:
        return false;
    }
  };

  const handleUpgrade = (tier: string) => {
    router.push(`/m/pricing?highlight=${tier}`);
  };

  return (
    <div className="px-3 py-4">
      {/* BVID Input */}
      <div className="mb-6">
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <input
              type="text"
              value={bvid}
              onChange={(e) => setBvid(e.target.value)}
              placeholder="输入B站BV号"
              disabled={!canUseFeature("custom_bvid")}
              className={`w-full px-4 py-3 pr-10 border rounded-xl text-sm ${
                canUseFeature("custom_bvid")
                  ? "border-gray-200 bg-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  : "border-gray-100 bg-gray-50 text-gray-400"
              }`}
            />
            <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          </div>
          <button
            onClick={() => handleAnalyze()}
            disabled={!canUseFeature("custom_bvid") || isLoading}
            className={`px-5 py-3 rounded-xl text-sm font-medium transition-colors ${
              canUseFeature("custom_bvid")
                ? "bg-blue-600 text-white hover:bg-blue-700"
                : "bg-gray-200 text-gray-400 cursor-not-allowed"
            }`}
          >
            {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : "解析"}
          </button>
        </div>
        {!canUseFeature("custom_bvid") && (
          <p className="mt-2 text-xs text-orange-500">
            自定义视频解析仅标准版/专业版可用
            <button
              onClick={() => handleUpgrade("standard")}
              className="ml-1 text-blue-600 underline"
            >
              立即升级
            </button>
          </p>
        )}
      </div>

      {/* Quota Cards */}
      {userStatus?.is_login && userStatus.quotas && (
        <div className="mb-6 grid grid-cols-3 gap-2">
          <QuotaCard
            title="今日自选"
            remaining={userStatus.quotas.day_self_analysis?.remaining || 0}
            total={userStatus.quotas.day_self_analysis?.total || 0}
            icon={Zap}
            color="blue"
          />
          <QuotaCard
            title="月度自定义"
            remaining={userStatus.quotas.month_custom_bvid?.remaining || 0}
            total={userStatus.quotas.month_custom_bvid?.total || 0}
            icon={Users}
            color="emerald"
            locked={!canUseFeature("custom_bvid")}
          />
          <QuotaCard
            title="对标诊断"
            remaining={userStatus.quotas.month_compare?.remaining || 0}
            total={userStatus.quotas.month_compare?.total || 0}
            icon={Crown}
            color="purple"
            locked={!canUseFeature("compare")}
          />
        </div>
      )}

      {/* Feature Cards */}
      <div className="space-y-3 mb-6">
        <FeatureCard
          title="榜单自选分析"
          description="对榜单视频进行AI分析"
          remaining={
            canUseFeature("self_analysis")
              ? `${userStatus?.quotas?.day_self_analysis?.remaining || 0}/${userStatus?.quotas?.day_self_analysis?.total || 0}`
              : undefined
          }
          icon={Zap}
          color="blue"
          locked={!canUseFeature("self_analysis")}
          onClick={() => {
            if (!userStatus?.is_login) {
              router.push("/login");
            } else if (!canUseFeature("self_analysis")) {
              handleUpgrade("light");
            } else {
              router.push("/m");
            }
          }}
        />

        <FeatureCard
          title="自定义视频解析"
          description="输入BVID深度分析任意视频"
          remaining={
            canUseFeature("custom_bvid")
              ? `${userStatus?.quotas?.month_custom_bvid?.remaining || 0}/${userStatus?.quotas?.month_custom_bvid?.total || 0}`
              : undefined
          }
          icon={Search}
          color="emerald"
          locked={!canUseFeature("custom_bvid")}
          onClick={() => {
            if (!userStatus?.is_login) {
              router.push("/login");
            } else if (!canUseFeature("custom_bvid")) {
              handleUpgrade("standard");
            }
          }}
        />

        <FeatureCard
          title="双视频对标诊断"
          description="对比两个视频的差异和优化空间"
          remaining={
            canUseFeature("compare")
              ? `${userStatus?.quotas?.month_compare?.remaining || 0}/${userStatus?.quotas?.month_compare?.total || 0}`
              : undefined
          }
          icon={Users}
          color="purple"
          locked={!canUseFeature("compare")}
          onClick={() => {
            if (!userStatus?.is_login) {
              router.push("/login");
            } else if (!canUseFeature("compare")) {
              handleUpgrade("standard");
            }
          }}
        />

        {canUseFeature("commercial") && (
          <FeatureCard
            title="账号商业化方案"
            description="专业版专属：获取账号变现方案"
            icon={Crown}
            color="orange"
            locked={false}
            onClick={() => {}}
          />
        )}
      </div>

      {/* Analysis Result */}
      {analysisResult && (
        <div className="bg-white rounded-xl p-4 shadow-sm">
          <h3 className="font-medium text-gray-800 mb-3">分析结果</h3>
          {analysisResult.cover_analysis && (
            <div className="mb-4">
              <h4 className="text-sm text-gray-500 mb-2">封面分析</h4>
              <div className="text-sm text-gray-700 space-y-1">
                <p>主体元素：{analysisResult.cover_analysis.cover_main_element}</p>
                <p>配色方案：{analysisResult.cover_analysis.cover_color_scheme}</p>
                <p>视觉风格：{analysisResult.cover_analysis.cover_visual_style}</p>
              </div>
            </div>
          )}
          {analysisResult.content_analysis && (
            <div>
              <h4 className="text-sm text-gray-500 mb-2">内容分析</h4>
              <div className="text-sm text-gray-700 space-y-1">
                <p>话题总结：{analysisResult.content_analysis.topic_summary}</p>
                {analysisResult.content_analysis.viral_logic_analysis && (
                  <p>爆款逻辑：{analysisResult.content_analysis.viral_logic_analysis}</p>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface QuotaCardProps {
  title: string;
  remaining: number;
  total: number;
  icon: React.ElementType;
  color: string;
  locked?: boolean;
}

function QuotaCard({ title, remaining, total, icon: Icon, color, locked }: QuotaCardProps) {
  const colorClasses = {
    blue: "bg-blue-50 text-blue-600",
    emerald: "bg-emerald-50 text-emerald-600",
    purple: "bg-purple-50 text-purple-600",
    orange: "bg-orange-50 text-orange-600",
  };

  return (
    <div className={`rounded-xl p-3 ${locked ? "bg-gray-100" : colorClasses[color as keyof typeof colorClasses]}`}>
      <div className="flex items-center gap-1 mb-1">
        <Icon className="w-4 h-4" />
        <span className="text-xs font-medium">{title}</span>
        {locked && <Lock className="w-3 h-3 ml-1" />}
      </div>
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

interface FeatureCardProps {
  title: string;
  description: string;
  remaining?: string;
  icon: React.ElementType;
  color: string;
  locked: boolean;
  onClick: () => void;
}

function FeatureCard({
  title,
  description,
  remaining,
  icon: Icon,
  color,
  locked,
  onClick,
}: FeatureCardProps) {
  const colorClasses = {
    blue: "border-blue-200 bg-blue-50",
    emerald: "border-emerald-200 bg-emerald-50",
    purple: "border-purple-200 bg-purple-50",
    orange: "border-orange-200 bg-orange-50",
  };

  return (
    <button
      onClick={onClick}
      className={`w-full p-4 rounded-xl border text-left transition-all ${
        locked ? "border-gray-100 bg-gray-50 opacity-60" : colorClasses[color as keyof typeof colorClasses]
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
            locked ? "bg-gray-200" : "bg-white"
          }`}>
            {locked ? (
              <Lock className="w-5 h-5 text-gray-400" />
            ) : (
              <Icon className={`w-5 h-5 ${
                color === "blue" ? "text-blue-600" :
                color === "emerald" ? "text-emerald-600" :
                color === "purple" ? "text-purple-600" :
                "text-orange-600"
              }`} />
            )}
          </div>
          <div>
            <h4 className="font-medium text-gray-800 text-sm">{title}</h4>
            <p className="text-xs text-gray-500">{description}</p>
          </div>
        </div>
        {remaining && (
          <div className="text-right">
            <span className="text-sm font-medium text-gray-800">{remaining}</span>
            <p className="text-xs text-gray-400">剩余</p>
          </div>
        )}
      </div>
    </button>
  );
}
