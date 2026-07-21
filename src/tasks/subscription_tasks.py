"""
订阅与额度相关定时任务
"""
from datetime import datetime
from src.tasks.scheduler import get_scheduler
from src.services.subscription_service import get_subscription_service
from src.services.quota_service import get_quota_service
from src.utils.database import get_db_session
from sqlalchemy import text


def daily_quota_reset_task() -> dict:
    """
    每日额度重置任务
    每日0点执行，重置所有用户当日自选分析额度
    """
    print(f"[{datetime.now().isoformat()}] Starting daily quota reset task...")

    quota_service = get_quota_service()
    reset_count = 0

    try:
        with get_db_session() as session:
            # 获取所有付费用户
            result = session.execute(
                text("""
                    SELECT id FROM users
                    WHERE user_level IN ('light', 'standard', 'pro')
                """)
            )
            users = result.fetchall()

            for (user_id,) in users:
                quota_service.reset_day_quota(user_id)
                reset_count += 1

        result = {
            "success": True,
            "reset_count": reset_count,
            "executed_at": datetime.now().isoformat(),
        }
        print(f"[{datetime.now().isoformat()}] Daily quota reset completed: {reset_count} users")

        return result
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] Daily quota reset failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "executed_at": datetime.now().isoformat(),
        }


def monthly_quota_reset_task() -> dict:
    """
    月度额度重置任务
    每月1号0点执行，清零用户月度自定义和对标诊断额度
    """
    print(f"[{datetime.now().isoformat()}] Starting monthly quota reset task...")

    reset_count = 0

    try:
        with get_db_session() as session:
            # 获取所有标准版和专业版用户
            result = session.execute(
                text("""
                    SELECT id, user_level FROM users
                    WHERE user_level IN ('standard', 'pro')
                """)
            )
            users = result.fetchall()

            for user_id, user_level in users:
                # 清零月度额度（通过删除Redis key让其自然重置）
                from src.services.quota_service import get_quota_service
                quota_service = get_quota_service()

                # 月度自定义BVID额度
                quota_service.reset_month_quota(user_id, "month_custom_bvid")
                # 月度对标诊断额度
                quota_service.reset_month_quota(user_id, "month_compare_diagnose")

                reset_count += 1

        result = {
            "success": True,
            "reset_count": reset_count,
            "executed_at": datetime.now().isoformat(),
        }
        print(f"[{datetime.now().isoformat()}] Monthly quota reset completed: {reset_count} users")

        return result
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] Monthly quota reset failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "executed_at": datetime.now().isoformat(),
        }


def subscription_expiry_check_task() -> dict:
    """
    订阅到期检测任务
    每小时执行一次，检测并自动降级过期订阅
    """
    print(f"[{datetime.now().isoformat()}] Starting subscription expiry check...")

    subscription_service = get_subscription_service()

    try:
        # 检查并降级过期订阅
        downgraded_count = subscription_service.check_and_downgrade_expired()

        result = {
            "success": True,
            "downgraded_count": downgraded_count,
            "executed_at": datetime.now().isoformat(),
        }
        print(f"[{datetime.now().isoformat()}] Subscription expiry check completed: {downgraded_count} users downgraded")

        return result
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] Subscription expiry check failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "executed_at": datetime.now().isoformat(),
        }


def subscription_renewal_reminder_task() -> dict:
    """
    订阅续费提醒任务
    每天检查订阅即将到期的用户（3天内），发送续费提醒
    """
    print(f"[{datetime.now().isoformat()}] Starting subscription renewal reminder check...")

    reminded_count = 0

    try:
        with get_db_session() as session:
            # 查找3天内即将到期的订阅
            result = session.execute(
                text("""
                    SELECT user_id, subscribe_tier, subscribe_expire
                    FROM users
                    WHERE subscribe_expire IS NOT NULL
                      AND subscribe_expire > CURRENT_TIMESTAMP
                      AND subscribe_expire <= CURRENT_TIMESTAMP + INTERVAL '3 days'
                """)
            )
            expiring = result.fetchall()

            for user_id, tier, expire_date in expiring:
                # 实际应用中这里应发送邮件/短信通知
                # 目前仅打印日志
                print(f"  Reminder: User {user_id} subscription ({tier}) expiring at {expire_date}")
                reminded_count += 1

        result = {
            "success": True,
            "reminded_count": reminded_count,
            "executed_at": datetime.now().isoformat(),
        }
        print(f"[{datetime.now().isoformat()}] Renewal reminder check completed: {reminded_count} reminders")

        return result
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] Renewal reminder check failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "executed_at": datetime.now().isoformat(),
        }


def auto_renew_task() -> dict:
    """
    自动续费处理任务
    每天检查开启自动续费的用户，自动创建新订阅订单
    """
    print(f"[{datetime.now().isoformat()}] Starting auto renew task...")

    renewed_count = 0
    failed_count = 0

    subscription_service = get_subscription_service()

    try:
        with get_db_session() as session:
            # 查找已过期但开启自动续费的订阅
            result = session.execute(
                text("""
                    SELECT so.user_id, so.tier, u.subscribe_expire
                    FROM subscribe_order so
                    JOIN users u ON so.user_id = u.id
                    WHERE so.status = 'paid'
                      AND so.auto_renew = TRUE
                      AND so.valid_until < CURRENT_TIMESTAMP
                """)
            )
            auto_renewals = result.fetchall()

            for user_id, tier, _ in auto_renewals:
                try:
                    # 创建新订单（模拟支付成功）
                    new_order = subscription_service.create_subscription(
                        user_id=user_id,
                        tier=tier,
                        payment_method="auto_renew"
                    )
                    if new_order:
                        # 直接标记为支付成功
                        subscription_service.process_payment(
                            new_order.id,
                            f"auto_renew_{new_order.id}_{datetime.now().timestamp()}"
                        )
                        renewed_count += 1
                        print(f"  Auto renewed: User {user_id} -> {tier}")
                except Exception as e:
                    failed_count += 1
                    print(f"  Auto renew failed for user {user_id}: {e}")

        result = {
            "success": True,
            "renewed_count": renewed_count,
            "failed_count": failed_count,
            "executed_at": datetime.now().isoformat(),
        }
        print(f"[{datetime.now().isoformat()}] Auto renew task completed: {renewed_count} renewed, {failed_count} failed")

        return result
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] Auto renew task failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "executed_at": datetime.now().isoformat(),
        }


def init_subscription_tasks() -> None:
    """
    初始化订阅与额度相关定时任务
    将任务注册到调度器
    """
    scheduler = get_scheduler()

    # 每日额度重置任务 - 每天0点执行
    scheduler.add_cron_task(
        task_id="daily_quota_reset",
        name="Daily Quota Reset",
        func=daily_quota_reset_task,
        hour=0,
        minute=0,
    )

    # 月度额度重置任务 - 每月1号0点执行
    scheduler.add_cron_task(
        task_id="monthly_quota_reset",
        name="Monthly Quota Reset",
        func=monthly_quota_reset_task,
        hour=0,
        minute=0,
        day_of_week="1st",  # 每月1号
    )

    # 订阅到期检测任务 - 每小时执行
    scheduler.add_interval_task(
        task_id="subscription_expiry_check",
        name="Subscription Expiry Check",
        func=subscription_expiry_check_task,
        interval_seconds=3600,  # 1小时
    )

    # 续费提醒任务 - 每天8点执行
    scheduler.add_cron_task(
        task_id="subscription_renewal_reminder",
        name="Subscription Renewal Reminder",
        func=subscription_renewal_reminder_task,
        hour=8,
        minute=0,
    )

    # 自动续费任务 - 每天1点执行
    scheduler.add_cron_task(
        task_id="auto_renew",
        name="Auto Renew",
        func=auto_renew_task,
        hour=1,
        minute=0,
    )
