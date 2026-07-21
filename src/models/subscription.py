"""
用户分层与订阅数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class UserLevel(str, Enum):
    """用户层级枚举"""
    TOURIST = "tourist"      # 游客，未登录
    FREE = "free"           # 免费注册用户
    LIGHT = "light"         # 轻量版 29元/月
    STANDARD = "standard"   # 标准版 89元/月
    PRO = "pro"             # 专业版 299元/月


class SubscribeTier(str, Enum):
    """订阅套餐枚举"""
    LIGHT = "light"         # 轻量版
    STANDARD = "standard"   # 标准版
    PRO = "pro"             # 专业版


class QuotaType(str, Enum):
    """额度类型枚举"""
    DAY_SELF_ANALYSIS = "day_self_analysis"           # 每日自选分析
    MONTH_CUSTOM_BVID = "month_custom_bvid"           # 月度自定义BVID
    MONTH_COMPARE_DIAGNOSE = "month_compare_diagnose"  # 月度对标诊断


class AnalysisType(str, Enum):
    """AI分析类型枚举"""
    COVER_ANALYSIS = "cover_analysis"           # 封面分析
    CONTENT_ANALYSIS = "content_analysis"       # 内容分析
    FRAME_EXTRACT = "frame_extract"              # 抽帧分析
    COMPARE_DIAGNOSE = "compare_diagnose"        # 对标诊断
    COMMERCIAL_REPORT = "commercial_report"      # 商业化报告


# 套餐价格配置
TIER_PRICES: Dict[SubscribeTier, float] = {
    SubscribeTier.LIGHT: 29.0,
    SubscribeTier.STANDARD: 89.0,
    SubscribeTier.PRO: 299.0,
}

# AI分析成本配置 (元/百万tokens)
AI_COST_INPUT = 0.6    # 输入0.6元/百万tokens
AI_COST_OUTPUT = 3.6    # 输出3.6元/百万tokens

# 单次分析token配置
ANALYSIS_TOKENS: Dict[AnalysisType, Dict[str, int]] = {
    AnalysisType.COVER_ANALYSIS: {"input": 1000, "output": 300},
    AnalysisType.CONTENT_ANALYSIS: {"input": 2000, "output": 500},
    AnalysisType.FRAME_EXTRACT: {"input": 8000, "output": 1000},
    AnalysisType.COMPARE_DIAGNOSE: {"input": 16000, "output": 2500},
    AnalysisType.COMMERCIAL_REPORT: {"input": 2000, "output": 1500},
}


def calculate_analysis_cost(analysis_type: AnalysisType, input_tokens: int = None, output_tokens: int = None) -> float:
    """计算单次分析成本"""
    tokens = ANALYSIS_TOKENS.get(analysis_type, {})
    input_t = input_tokens or tokens.get("input", 0)
    output_t = output_tokens or tokens.get("output", 0)

    cost = (input_t / 1_000_000) * AI_COST_INPUT + (output_t / 1_000_000) * AI_COST_OUTPUT
    return round(cost, 6)


@dataclass
class UserQuota:
    """用户额度模型"""
    id: Optional[int] = None
    user_id: int = 0
    quota_type: QuotaType = QuotaType.DAY_SELF_ANALYSIS
    used_count: int = 0
    total_count: int = 0
    period_start: datetime = field(default_factory=datetime.now)
    period_end: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def remaining(self) -> int:
        """剩余额度"""
        return max(0, self.total_count - self.used_count)

    def is_expired(self) -> bool:
        """是否过期"""
        return datetime.now() > self.period_end

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "quota_type": self.quota_type.value,
            "used_count": self.used_count,
            "total_count": self.total_count,
            "remaining": self.remaining(),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
        }


@dataclass
class SubscribeOrder:
    """订阅订单模型"""
    id: Optional[int] = None
    user_id: int = 0
    tier: SubscribeTier = SubscribeTier.LIGHT
    price: float = 0.0
    status: str = "pending"  # pending/paid/cancelled/expired
    payment_method: Optional[str] = None
    transaction_id: Optional[str] = None
    valid_from: datetime = field(default_factory=datetime.now)
    valid_until: datetime = field(default_factory=datetime.now)
    auto_renew: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def is_valid(self) -> bool:
        """订单是否有效"""
        return self.status == "paid" and datetime.now() < self.valid_until

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "tier": self.tier.value,
            "price": self.price,
            "status": self.status,
            "payment_method": self.payment_method,
            "valid_from": self.valid_from.isoformat(),
            "valid_until": self.valid_until.isoformat(),
            "auto_renew": self.auto_renew,
        }


@dataclass
class PermissionConfig:
    """权限配置模型"""
    id: Optional[int] = None
    tier: UserLevel = UserLevel.FREE
    permission_key: str = ""
    permission_value: str = ""
    description: Optional[str] = None

    def get_int_value(self, default: int = 0) -> int:
        """获取整数值"""
        try:
            return int(self.permission_value)
        except ValueError:
            return default

    def get_bool_value(self, default: bool = False) -> bool:
        """获取布尔值"""
        if self.permission_value.lower() in ("true", "1", "yes"):
            return True
        elif self.permission_value.lower() in ("false", "0", "no"):
            return False
        return default

    def to_dict(self) -> dict:
        return {
            "tier": self.tier.value,
            "permission_key": self.permission_key,
            "permission_value": self.permission_value,
        }
