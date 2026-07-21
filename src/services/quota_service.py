"""
用户额度服务
基于Redis的额度扣减与管理
"""
import json
import redis
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from src.config import settings
from src.models.subscription import QuotaType, UserLevel, TIER_PRICES


class QuotaService:
    """用户额度服务"""

    # Redis key前缀
    KEY_TRIAL = "trial:ip:{ip}"                    # 游客试用次数
    KEY_DAY_QUOTA = "quota:day:{user_id}"         # 每日自选分析额度
    KEY_MONTH_QUOTA = "quota:month:{user_id}:{quota_type}"  # 月度额度

    # 每日自选分析配额（轻量/标准/专业用户）
    DAY_SELF_ANALYSIS_QUOTA = 10

    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    def _get_trial_key(self, ip: str) -> str:
        return self.KEY_TRIAL.format(ip=ip)

    def _get_day_quota_key(self, user_id: int) -> str:
        return self.KEY_DAY_QUOTA.format(user_id=user_id)

    def _get_month_quota_key(self, user_id: int, quota_type: str) -> str:
        return self.KEY_MONTH_QUOTA.format(user_id=user_id, quota_type=quota_type)

    # ============== 游客试用次数管理 ==============

    def get_trial_remaining(self, ip: str) -> int:
        """获取游客剩余试用次数"""
        key = self._get_trial_key(ip)
        count = self.redis_client.get(key)
        if count is None:
            return 3  # 默认3次
        return max(0, int(count))

    def decrement_trial(self, ip: str) -> int:
        """扣减游客试用次数，返回剩余次数"""
        key = self._get_trial_key(ip)
        count = self.redis_client.incr(key, -1)
        if count < 0:
            self.redis_client.set(key, 0)
            return 0
        # 设置24小时过期
        self.redis_client.expire(key, 86400)
        return max(0, count)

    def reset_trial(self, ip: str) -> None:
        """重置游客试用次数"""
        key = self._get_trial_key(ip)
        self.redis_client.set(key, 3)
        self.redis_client.expire(key, 86400)

    # ============== 每日自选分析额度 ==============

    def get_day_quota_remaining(self, user_id: int) -> int:
        """获取每日自选分析剩余额度"""
        key = self._get_day_quota_key(user_id)
        quota_json = self.redis_client.get(key)

        if quota_json is None:
            return self.DAY_SELF_ANALYSIS_QUOTA

        data = json.loads(quota_json)
        # 检查是否过期
        if datetime.now().isoformat() > data.get("expire_at", ""):
            # 已过期，重置
            return self.DAY_SELF_ANALYSIS_QUOTA

        return max(0, int(data.get("remaining", 0)))

    def decrement_day_quota(self, user_id: int) -> tuple[bool, int]:
        """
        扣减每日自选分析额度
        返回: (是否成功, 剩余额度)
        """
        key = self._get_day_quota_key(user_id)
        quota_json = self.redis_client.get(key)

        now = datetime.now()
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        if quota_json is None:
            # 首次使用，设置额度
            remaining = self.DAY_SELF_ANALYSIS_QUOTA - 1
            data = {
                "remaining": remaining,
                "expire_at": today_end.isoformat()
            }
            self.redis_client.set(key, json.dumps(data))
            self.redis_client.expire(key, 86400)  # 24小时过期
            return (True, remaining)

        data = json.loads(quota_json)

        # 检查是否过期
        if now.isoformat() > data.get("expire_at", ""):
            # 已过期，重置额度
            remaining = self.DAY_SELF_ANALYSIS_QUOTA - 1
            data = {
                "remaining": remaining,
                "expire_at": today_end.isoformat()
            }
            self.redis_client.set(key, json.dumps(data))
            self.redis_client.expire(key, 86400)
            return (True, remaining)

        remaining = int(data.get("remaining", 0))
        if remaining <= 0:
            return (False, 0)

        remaining -= 1
        data["remaining"] = remaining
        self.redis_client.set(key, json.dumps(data))
        return (True, remaining)

    def reset_day_quota(self, user_id: int) -> None:
        """重置每日自选分析额度"""
        key = self._get_day_quota_key(user_id)
        self.redis_client.delete(key)

    def reset_month_quota(self, user_id: int, quota_type: str) -> None:
        """重置月度额度"""
        key = self._get_month_quota_key(user_id, quota_type)
        self.redis_client.delete(key)

    # ============== 月度额度 ==============

    def get_month_quota_remaining(self, user_id: int, quota_type: QuotaType) -> int:
        """获取月度额度剩余"""
        key = self._get_month_quota_key(user_id, quota_type.value)
        quota_json = self.redis_client.get(key)

        if quota_json is None:
            return 0

        data = json.loads(quota_json)
        # 检查是否过期
        if datetime.now().isoformat() > data.get("expire_at", ""):
            return 0

        return max(0, int(data.get("remaining", 0)))

    def decrement_month_quota(self, user_id: int, quota_type: QuotaType, max_quota: int) -> tuple[bool, int]:
        """
        扣减月度额度
        返回: (是否成功, 剩余额度)
        """
        key = self._get_month_quota_key(user_id, quota_type.value)
        quota_json = self.redis_client.get(key)

        now = datetime.now()
        # 计算本月结束时间
        if now.month == 12:
            month_end = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            month_end = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)

        if quota_json is None:
            # 首次使用，设置额度
            remaining = max_quota - 1
            data = {
                "remaining": remaining,
                "max": max_quota,
                "expire_at": month_end.isoformat()
            }
            self.redis_client.set(key, json.dumps(data))
            # 设置30天过期
            self.redis_client.expire(key, 2592000)
            return (True, remaining)

        data = json.loads(quota_json)

        # 检查是否过期
        if now.isoformat() > data.get("expire_at", ""):
            # 已过期，重置额度
            remaining = max_quota - 1
            data = {
                "remaining": remaining,
                "max": max_quota,
                "expire_at": month_end.isoformat()
            }
            self.redis_client.set(key, json.dumps(data))
            self.redis_client.expire(key, 2592000)
            return (True, remaining)

        remaining = int(data.get("remaining", 0))
        if remaining <= 0:
            return (False, 0)

        remaining -= 1
        data["remaining"] = remaining
        self.redis_client.set(key, json.dumps(data))
        return (True, remaining)

    # ============== 统一额度检查 ==============

    def check_and_decrement_quota(
        self,
        user_id: int,
        user_level: UserLevel,
        quota_type: QuotaType
    ) -> tuple[bool, str, int]:
        """
        统一额度检查与扣减
        返回: (是否成功, 错误信息, 剩余额度)

        错误码:
        - "trial_exhausted": 试用次数耗尽
        - "day_quota_exhausted": 每日额度耗尽
        - "month_quota_exhausted": 月度额度耗尽
        - "permission_denied": 权限不足
        """
        # 游客试用次数检查
        if user_level == UserLevel.TOURIST:
            return (False, "trial_exhausted", 0)

        # 免费用户无额度
        if user_level == UserLevel.FREE:
            return (False, "permission_denied", 0)

        # 每日自选分析
        if quota_type == QuotaType.DAY_SELF_ANALYSIS:
            if user_level == UserLevel.LIGHT or user_level == UserLevel.STANDARD or user_level == UserLevel.PRO:
                return self.decrement_day_quota(user_id)
            return (False, "permission_denied", 0)

        # 月度自定义BVID
        if quota_type == QuotaType.MONTH_CUSTOM_BVID:
            if user_level == UserLevel.STANDARD:
                return self.decrement_month_quota(user_id, quota_type, 150)
            elif user_level == UserLevel.PRO:
                return self.decrement_month_quota(user_id, quota_type, 500)
            return (False, "permission_denied", 0)

        # 月度对标诊断
        if quota_type == QuotaType.MONTH_COMPARE_DIAGNOSE:
            if user_level == UserLevel.STANDARD:
                return self.decrement_month_quota(user_id, quota_type, 30)
            elif user_level == UserLevel.PRO:
                return self.decrement_month_quota(user_id, quota_type, 100)
            return (False, "permission_denied", 0)

        return (False, "permission_denied", 0)

    def get_all_quotas(self, user_id: int, user_level: UserLevel) -> Dict[str, Any]:
        """获取用户所有额度信息"""
        quotas = {}

        if user_level == UserLevel.TOURIST:
            return {"level": "tourist"}

        if user_level == UserLevel.FREE:
            return {
                "level": "free",
                "day_self_analysis": {"remaining": 0, "total": 0},
                "month_custom_bvid": {"remaining": 0, "total": 0},
                "month_compare": {"remaining": 0, "total": 0},
            }

        # 每日自选分析
        quotas["day_self_analysis"] = {
            "remaining": self.get_day_quota_remaining(user_id),
            "total": self.DAY_SELF_ANALYSIS_QUOTA,
        }

        # 月度自定义BVID
        if user_level == UserLevel.STANDARD:
            quotas["month_custom_bvid"] = {
                "remaining": self.get_month_quota_remaining(user_id, QuotaType.MONTH_CUSTOM_BVID),
                "total": 150,
            }
            quotas["month_compare"] = {
                "remaining": self.get_month_quota_remaining(user_id, QuotaType.MONTH_COMPARE_DIAGNOSE),
                "total": 30,
            }
        elif user_level == UserLevel.PRO:
            quotas["month_custom_bvid"] = {
                "remaining": self.get_month_quota_remaining(user_id, QuotaType.MONTH_CUSTOM_BVID),
                "total": 500,
            }
            quotas["month_compare"] = {
                "remaining": self.get_month_quota_remaining(user_id, QuotaType.MONTH_COMPARE_DIAGNOSE),
                "total": 100,
            }
        else:
            quotas["month_custom_bvid"] = {"remaining": 0, "total": 0}
            quotas["month_compare"] = {"remaining": 0, "total": 0}

        quotas["level"] = user_level.value
        return quotas


# 全局单例
_quota_service: Optional[QuotaService] = None


def get_quota_service() -> QuotaService:
    """获取额度服务单例"""
    global _quota_service
    if _quota_service is None:
        _quota_service = QuotaService()
    return _quota_service
