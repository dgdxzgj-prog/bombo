"""
订阅服务
处理订阅创建、支付、续费、降级等逻辑
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from src.models.subscription import SubscribeTier, TIER_PRICES, SubscribeOrder
from src.models.user import User, UserLevel
from src.utils.database import get_db_session
from sqlalchemy import text


class SubscriptionService:
    """订阅服务"""

    # 套餐有效期（月）
    TIER_DURATION_MONTHS = {
        SubscribeTier.LIGHT: 1,
        SubscribeTier.STANDARD: 1,
        SubscribeTier.PRO: 1,
    }

    def create_subscription(
        self,
        user_id: int,
        tier: SubscribeTier,
        payment_method: str = "wechat"
    ) -> Optional[SubscribeOrder]:
        """
        创建订阅订单

        Args:
            user_id: 用户ID
            tier: 订阅套餐
            payment_method: 支付方式

        Returns:
            SubscribeOrder 订单对象
        """
        price = TIER_PRICES.get(tier, 0)
        duration_months = self.TIER_DURATION_MONTHS.get(tier, 1)

        now = datetime.now()
        valid_until = now + timedelta(days=30 * duration_months)

        order = SubscribeOrder(
            user_id=user_id,
            tier=tier,
            price=price,
            status="pending",
            payment_method=payment_method,
            valid_from=now,
            valid_until=valid_until,
            auto_renew=False,
        )

        try:
            with get_db_session() as session:
                # 插入订单
                result = session.execute(
                    text("""
                        INSERT INTO subscribe_order
                        (user_id, tier, price, status, payment_method, valid_from, valid_until, auto_renew)
                        VALUES (:user_id, :tier, :price, :status, :payment_method, :valid_from, :valid_until, :auto_renew)
                        RETURNING id
                    """),
                    {
                        "user_id": order.user_id,
                        "tier": order.tier.value,
                        "price": order.price,
                        "status": order.status,
                        "payment_method": order.payment_method,
                        "valid_from": order.valid_from,
                        "valid_until": order.valid_until,
                        "auto_renew": order.auto_renew,
                    }
                )
                order_id = result.fetchone()[0]
                order.id = order_id

            return order
        except Exception as e:
            print(f"Failed to create subscription order: {e}")
            return None

    def process_payment(
        self,
        order_id: int,
        transaction_id: str
    ) -> bool:
        """
        处理支付成功回调

        Args:
            order_id: 订单ID
            transaction_id: 支付平台交易号

        Returns:
            是否成功
        """
        try:
            with get_db_session() as session:
                # 更新订单状态
                session.execute(
                    text("""
                        UPDATE subscribe_order
                        SET status = 'paid',
                            transaction_id = :transaction_id,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :order_id AND status = 'pending'
                    """),
                    {"order_id": order_id, "transaction_id": transaction_id}
                )

                # 获取订单信息以更新用户权限
                result = session.execute(
                    text("SELECT user_id, tier, valid_until FROM subscribe_order WHERE id = :order_id"),
                    {"order_id": order_id}
                )
                row = result.fetchone()
                if not row:
                    return False

                user_id, tier, valid_until = row

                # 更新用户层级和订阅信息
                user_level = self._tier_to_user_level(tier)
                session.execute(
                    text("""
                        UPDATE users
                        SET user_level = :user_level,
                            subscribe_tier = :subscribe_tier,
                            subscribe_expire = :subscribe_expire,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :user_id
                    """),
                    {
                        "user_level": user_level.value,
                        "subscribe_tier": tier,
                        "subscribe_expire": valid_until,
                        "user_id": user_id,
                    }
                )

            return True
        except Exception as e:
            print(f"Failed to process payment: {e}")
            return False

    def cancel_subscription(self, user_id: int) -> bool:
        """
        取消订阅（不退款，到期后降级）

        Args:
            user_id: 用户ID

        Returns:
            是否成功
        """
        try:
            with get_db_session() as session:
                # 更新订单状态
                session.execute(
                    text("""
                        UPDATE subscribe_order
                        SET status = 'cancelled',
                            auto_renew = FALSE,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = :user_id AND status = 'paid'
                    """),
                    {"user_id": user_id}
                )

                # 关闭自动续费
                session.execute(
                    text("""
                        UPDATE subscribe_order
                        SET auto_renew = FALSE
                        WHERE user_id = :user_id AND status = 'paid'
                    """),
                    {"user_id": user_id}
                )

            return True
        except Exception as e:
            print(f"Failed to cancel subscription: {e}")
            return False

    def enable_auto_renew(self, user_id: int) -> bool:
        """开启自动续费"""
        try:
            with get_db_session() as session:
                session.execute(
                    text("""
                        UPDATE subscribe_order
                        SET auto_renew = TRUE,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = :user_id AND status = 'paid'
                    """),
                    {"user_id": user_id}
                )
            return True
        except Exception as e:
            print(f"Failed to enable auto renew: {e}")
            return False

    def disable_auto_renew(self, user_id: int) -> bool:
        """关闭自动续费"""
        try:
            with get_db_session() as session:
                session.execute(
                    text("""
                        UPDATE subscribe_order
                        SET auto_renew = FALSE,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = :user_id AND status = 'paid'
                    """),
                    {"user_id": user_id}
                )
            return True
        except Exception as e:
            print(f"Failed to disable auto renew: {e}")
            return False

    def check_and_downgrade_expired(self) -> int:
        """
        检查并降级过期订阅

        Returns:
            降级用户数量
        """
        try:
            with get_db_session() as session:
                # 查找已过期的付费用户
                result = session.execute(
                    text("""
                        SELECT id, subscribe_tier
                        FROM users
                        WHERE subscribe_expire < CURRENT_TIMESTAMP
                          AND subscribe_tier IS NOT NULL
                    """)
                )
                expired_users = result.fetchall()

                count = 0
                for user_id, tier in expired_users:
                    # 降级到免费用户
                    session.execute(
                        text("""
                            UPDATE users
                            SET user_level = 'free',
                                subscribe_tier = NULL,
                                subscribe_expire = NULL,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = :user_id
                        """),
                        {"user_id": user_id}
                    )
                    count += 1

                # 更新过期订单状态
                session.execute(
                    text("""
                        UPDATE subscribe_order
                        SET status = 'expired',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE valid_until < CURRENT_TIMESTAMP
                          AND status = 'paid'
                    """)
                )

            return count
        except Exception as e:
            print(f"Failed to check expired subscriptions: {e}")
            return 0

    def get_user_subscription(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        获取用户当前订阅信息

        Args:
            user_id: 用户ID

        Returns:
            订阅信息字典
        """
        try:
            with get_db_session() as session:
                result = session.execute(
                    text("""
                        SELECT id, tier, price, status, valid_from, valid_until, auto_renew, created_at
                        FROM subscribe_order
                        WHERE user_id = :user_id AND status = 'paid'
                        ORDER BY created_at DESC
                        LIMIT 1
                    """),
                    {"user_id": user_id}
                )
                row = result.fetchone()

                if not row:
                    return None

                return {
                    "order_id": row[0],
                    "tier": row[1],
                    "price": float(row[2]),
                    "status": row[3],
                    "valid_from": row[4].isoformat() if row[4] else None,
                    "valid_until": row[5].isoformat() if row[5] else None,
                    "auto_renew": row[6],
                    "created_at": row[7].isoformat() if row[7] else None,
                }
        except Exception as e:
            print(f"Failed to get user subscription: {e}")
            return None

    def get_subscription_tiers(self) -> List[Dict[str, Any]]:
        """获取所有订阅套餐信息"""
        return [
            {
                "tier": "light",
                "name": "轻量版",
                "price": TIER_PRICES.get(SubscribeTier.LIGHT, 29),
                "features": [
                    "每日10次榜单视频自选AI分析",
                    "视频抽帧拆解能力",
                    "各赛道前40条视频基础分析",
                ],
                "limits": {
                    "day_self_analysis": 10,
                    "month_custom_bvid": 0,
                    "month_compare": 0,
                }
            },
            {
                "tier": "standard",
                "name": "标准版",
                "price": TIER_PRICES.get(SubscribeTier.STANDARD, 89),
                "features": [
                    "每日10次榜单视频自选AI分析",
                    "视频抽帧拆解能力",
                    "月度150次自定义BVID分析",
                    "月度30次对标诊断",
                    "赛道全部视频基础分析",
                ],
                "limits": {
                    "day_self_analysis": 10,
                    "month_custom_bvid": 150,
                    "month_compare": 30,
                }
            },
            {
                "tier": "pro",
                "name": "专业版",
                "price": TIER_PRICES.get(SubscribeTier.PRO, 299),
                "features": [
                    "不限次数榜单视频自选AI分析",
                    "视频抽帧拆解能力（无限制）",
                    "月度500次自定义BVID分析",
                    "月度100次对标诊断",
                    "专属账号商业化诊断报告",
                    "赛道/设备/剪辑软件智能推荐",
                    "全功能无任何条数限制",
                ],
                "limits": {
                    "day_self_analysis": 999999,
                    "month_custom_bvid": 500,
                    "month_compare": 100,
                }
            },
        ]

    def _tier_to_user_level(self, tier: str) -> UserLevel:
        """将订阅套餐转换为用户层级"""
        mapping = {
            "light": UserLevel.LIGHT,
            "standard": UserLevel.STANDARD,
            "pro": UserLevel.PRO,
        }
        return mapping.get(tier, UserLevel.FREE)


# 全局单例
_subscription_service: Optional[SubscriptionService] = None


def get_subscription_service() -> SubscriptionService:
    """获取订阅服务单例"""
    global _subscription_service
    if _subscription_service is None:
        _subscription_service = SubscriptionService()
    return _subscription_service
