"""
权限服务
基于用户层级的功能与数据权限控制
"""
from typing import Optional, Dict, Any
from src.models.user import User, UserLevel
from src.models.subscription import TIER_PRICES


class PermissionService:
    """权限服务"""

    # 各层级视频榜单可见条数
    VIDEO_LIST_LIMITS: Dict[UserLevel, int] = {
        UserLevel.TOURIST: 40,
        UserLevel.FREE: 999999,
        UserLevel.LIGHT: 999999,
        UserLevel.STANDARD: 999999,
        UserLevel.PRO: 999999,
    }

    # 各层级基础AI分析条数限制
    AI_ANALYSIS_LIMITS: Dict[UserLevel, int] = {
        UserLevel.TOURIST: 32,
        UserLevel.FREE: 32,
        UserLevel.LIGHT: 40,
        UserLevel.STANDARD: 999999,
        UserLevel.PRO: 999999,
    }

    # 各层级功能权限
    FEATURE_PERMISSIONS: Dict[str, Dict[UserLevel, bool]] = {
        "frame_extract": {  # 抽帧分析
            UserLevel.TOURIST: False,
            UserLevel.FREE: False,
            UserLevel.LIGHT: True,
            UserLevel.STANDARD: True,
            UserLevel.PRO: True,
        },
        "custom_bvid": {  # 自定义BVID分析
            UserLevel.TOURIST: False,
            UserLevel.FREE: False,
            UserLevel.LIGHT: False,
            UserLevel.STANDARD: True,
            UserLevel.PRO: True,
        },
        "compare_diagnose": {  # 对标诊断
            UserLevel.TOURIST: False,
            UserLevel.FREE: False,
            UserLevel.LIGHT: False,
            UserLevel.STANDARD: True,
            UserLevel.PRO: True,
        },
        "commercial_report": {  # 商业化报告
            UserLevel.TOURIST: False,
            UserLevel.FREE: False,
            UserLevel.LIGHT: False,
            UserLevel.STANDARD: False,
            UserLevel.PRO: True,
        },
    }

    def get_video_list_limit(self, user: User) -> int:
        """获取视频榜单可见条数限制"""
        return self.VIDEO_LIST_LIMITS.get(user.user_level, 40)

    def get_ai_analysis_limit(self, user: User) -> int:
        """获取基础AI分析条数限制"""
        return self.AI_ANALYSIS_LIMITS.get(user.user_level, 32)

    def can_use_feature(self, user: User, feature: str) -> bool:
        """检查用户是否可以使用某功能"""
        if feature not in self.FEATURE_PERMISSIONS:
            return False
        return self.FEATURE_PERMISSIONS[feature].get(user.user_level, False)

    def can_view_ai_analysis(self, user: User, video_index: int) -> bool:
        """
        检查用户是否可以查看AI分析
        video_index: 视频在榜单中的索引（从0开始）
        """
        limit = self.get_ai_analysis_limit(user)
        return video_index < limit

    def can_do_frame_extract(self, user: User, video_index: int = None) -> bool:
        """检查用户是否可以进行抽帧分析"""
        if not self.can_use_feature(user, "frame_extract"):
            return False
        # 轻量版限制榜单内前40条
        if user.user_level == UserLevel.LIGHT and video_index is not None:
            return video_index < 40
        return True

    def can_custom_bvid_analysis(self, user: User) -> bool:
        """检查用户是否可以进行自定义BVID分析"""
        return self.can_use_feature(user, "custom_bvid")

    def can_compare_diagnose(self, user: User) -> bool:
        """检查用户是否可以进行对标诊断"""
        return self.can_use_feature(user, "compare_diagnose")

    def can_commercial_report(self, user: User) -> bool:
        """检查用户是否可以生成商业化报告"""
        return self.can_use_feature(user, "commercial_report")

    def get_upgrade_pop_type(self, user: User, feature: str) -> Optional[str]:
        """
        获取用户触发升级弹窗的类型
        返回None表示不需要弹窗
        """
        level = user.user_level

        # 游客试用耗尽
        if level == UserLevel.TOURIST and user.trial_count <= 0:
            return "trial_exhausted"

        # 免费用户尝试高级功能
        if level == UserLevel.FREE:
            if feature in ("frame_extract", "ai_analysis"):
                return "free_upgrade"
            if feature in ("custom_bvid", "compare_diagnose"):
                return "light_upgrade"

        # 轻量版尝试自定义功能
        if level == UserLevel.LIGHT:
            if feature in ("custom_bvid", "compare_diagnose"):
                return "standard_upgrade"

        # 标准版尝试专业功能
        if level == UserLevel.STANDARD:
            if feature == "commercial_report":
                return "pro_upgrade"

        return None

    def get_user_status_info(self, user: User) -> Dict[str, Any]:
        """获取用户状态信息，用于前端展示"""
        info = {
            "user_level": user.user_level.value,
            "is_paid": user.is_paid_user(),
            "tier": user.subscribe_tier,
            "subscribe_expire": user.subscribe_expire.isoformat() if user.subscribe_expire else None,
        }

        # 各层级状态标签
        status_labels = {
            UserLevel.TOURIST: "游客",
            UserLevel.FREE: "免费用户",
            UserLevel.LIGHT: "轻量版",
            UserLevel.STANDARD: "标准版",
            UserLevel.PRO: "专业版",
        }
        info["status_label"] = status_labels.get(user.user_level, "未知")

        # 升级提示
        upgrade_hints = {
            UserLevel.TOURIST: "登录解锁完整榜单基础分析",
            UserLevel.FREE: "升级解锁视频抽帧拆解",
            UserLevel.LIGHT: "升级解锁自定义视频解析",
            UserLevel.STANDARD: "升级解锁专属商业化工具",
            UserLevel.PRO: None,
        }
        info["upgrade_hint"] = upgrade_hints.get(user.user_level)

        # 可用套餐及价格
        if user.user_level == UserLevel.TOURIST or user.user_level == UserLevel.FREE:
            info["upgrade_tiers"] = [
                {"tier": "light", "price": TIER_PRICES.get("light", 29)},
                {"tier": "standard", "price": TIER_PRICES.get("standard", 89)},
                {"tier": "pro", "price": TIER_PRICES.get("pro", 299)},
            ]
        elif user.user_level == UserLevel.LIGHT:
            info["upgrade_tiers"] = [
                {"tier": "standard", "price": TIER_PRICES.get("standard", 89)},
                {"tier": "pro", "price": TIER_PRICES.get("pro", 299)},
            ]
        elif user.user_level == UserLevel.STANDARD:
            info["upgrade_tiers"] = [
                {"tier": "pro", "price": TIER_PRICES.get("pro", 299)},
            ]
        else:
            info["upgrade_tiers"] = []

        return info


# 全局单例
_permission_service: Optional[PermissionService] = None


def get_permission_service() -> PermissionService:
    """获取权限服务单例"""
    global _permission_service
    if _permission_service is None:
        _permission_service = PermissionService()
    return _permission_service
