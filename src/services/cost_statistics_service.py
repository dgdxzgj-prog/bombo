"""
AI成本统计服务
记录和分析AI调用的token消耗与成本
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from src.models.subscription import AnalysisType, AI_COST_INPUT, AI_COST_OUTPUT, calculate_analysis_cost
from src.utils.database import get_db_session
from sqlalchemy import text


class CostStatisticsService:
    """AI成本统计服务"""

    def log_analysis_cost(
        self,
        user_id: Optional[int],
        bvid: str,
        analysis_type: str,
        input_tokens: int,
        output_tokens: int,
        duration_ms: int = 0
    ) -> bool:
        """
        记录一次AI分析的成本

        Args:
            user_id: 用户ID（可为None表示系统调用）
            bvid: 视频BV号
            analysis_type: 分析类型
            input_tokens: 输入token数
            output_tokens: 输出token数
            duration_ms: 耗时毫秒

        Returns:
            是否成功
        """
        try:
            # 计算成本
            analysis_type_enum = AnalysisType(analysis_type) if analysis_type in [e.value for e in AnalysisType] else None
            if analysis_type_enum:
                total_cost = calculate_analysis_cost(analysis_type_enum, input_tokens, output_tokens)
                input_cost = (input_tokens / 1_000_000) * AI_COST_INPUT
                output_cost = (output_tokens / 1_000_000) * AI_COST_OUTPUT
            else:
                total_cost = 0
                input_cost = 0
                output_cost = 0

            with get_db_session() as session:
                session.execute(
                    text("""
                        INSERT INTO ai_cost_log
                        (user_id, bvid, analysis_type, input_tokens, output_tokens,
                         input_cost, output_cost, total_cost, duration_ms)
                        VALUES (:user_id, :bvid, :analysis_type, :input_tokens, :output_tokens,
                                :input_cost, :output_cost, :total_cost, :duration_ms)
                    """),
                    {
                        "user_id": user_id,
                        "bvid": bvid,
                        "analysis_type": analysis_type,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "input_cost": input_cost,
                        "output_cost": output_cost,
                        "total_cost": total_cost,
                        "duration_ms": duration_ms,
                    }
                )
            return True
        except Exception as e:
            print(f"Failed to log analysis cost: {e}")
            return False

    def get_daily_cost(self, date: datetime = None) -> Dict[str, Any]:
        """
        获取指定日期的成本统计

        Args:
            date: 日期（默认为今天）

        Returns:
            成本统计字典
        """
        if date is None:
            date = datetime.now()

        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)

        try:
            with get_db_session() as session:
                # 按分析类型汇总
                result = session.execute(
                    text("""
                        SELECT
                            analysis_type,
                            COUNT(*) as call_count,
                            SUM(input_tokens) as total_input_tokens,
                            SUM(output_tokens) as total_output_tokens,
                            SUM(input_cost) as total_input_cost,
                            SUM(output_cost) as total_output_cost,
                            SUM(total_cost) as total_cost
                        FROM ai_cost_log
                        WHERE created_at >= :start_time AND created_at <= :end_time
                        GROUP BY analysis_type
                    """),
                    {"start_time": start_of_day, "end_time": end_of_day}
                )

                by_type = []
                total_cost = 0
                total_calls = 0

                for row in result.fetchall():
                    type_cost = float(row[6] or 0)
                    type_calls = int(row[1] or 0)
                    by_type.append({
                        "analysis_type": row[0],
                        "call_count": type_calls,
                        "input_tokens": int(row[2] or 0),
                        "output_tokens": int(row[3] or 0),
                        "input_cost": float(row[4] or 0),
                        "output_cost": float(row[5] or 0),
                        "total_cost": type_cost,
                    })
                    total_cost += type_cost
                    total_calls += type_calls

                return {
                    "date": date.strftime("%Y-%m-%d"),
                    "total_cost": round(total_cost, 4),
                    "total_calls": total_calls,
                    "by_type": by_type,
                }
        except Exception as e:
            print(f"Failed to get daily cost: {e}")
            return {
                "date": date.strftime("%Y-%m-%d"),
                "total_cost": 0,
                "total_calls": 0,
                "by_type": [],
            }

    def get_monthly_cost(self, year: int = None, month: int = None) -> Dict[str, Any]:
        """
        获取指定月份的成本统计

        Args:
            year: 年份（默认为当前年份）
            month: 月份（默认为当前月份）

        Returns:
            月度成本统计字典
        """
        now = datetime.now()
        if year is None:
            year = now.year
        if month is None:
            month = now.month

        start_of_month = datetime(year, month, 1)
        if month == 12:
            end_of_month = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end_of_month = datetime(year, month + 1, 1) - timedelta(seconds=1)

        try:
            with get_db_session() as session:
                # 按分析类型汇总
                result = session.execute(
                    text("""
                        SELECT
                            analysis_type,
                            COUNT(*) as call_count,
                            SUM(input_tokens) as total_input_tokens,
                            SUM(output_tokens) as total_output_tokens,
                            SUM(input_cost) as total_input_cost,
                            SUM(output_cost) as total_output_cost,
                            SUM(total_cost) as total_cost
                        FROM ai_cost_log
                        WHERE created_at >= :start_time AND created_at <= :end_time
                        GROUP BY analysis_type
                    """),
                    {"start_time": start_of_month, "end_time": end_of_month}
                )

                by_type = []
                total_cost = 0
                total_calls = 0

                for row in result.fetchall():
                    type_cost = float(row[6] or 0)
                    type_calls = int(row[1] or 0)
                    by_type.append({
                        "analysis_type": row[0],
                        "call_count": type_calls,
                        "input_tokens": int(row[2] or 0),
                        "output_tokens": int(row[3] or 0),
                        "input_cost": float(row[4] or 0),
                        "output_cost": float(row[5] or 0),
                        "total_cost": type_cost,
                    })
                    total_cost += type_cost
                    total_calls += type_calls

                # 按日汇总
                daily_result = session.execute(
                    text("""
                        SELECT
                            DATE(created_at) as call_date,
                            COUNT(*) as call_count,
                            SUM(total_cost) as daily_cost
                        FROM ai_cost_log
                        WHERE created_at >= :start_time AND created_at <= :end_time
                        GROUP BY DATE(created_at)
                        ORDER BY call_date
                    """),
                    {"start_time": start_of_month, "end_time": end_of_month}
                )

                daily = []
                for row in daily_result.fetchall():
                    daily.append({
                        "date": row[0].strftime("%Y-%m-%d") if hasattr(row[0], 'strftime') else str(row[0]),
                        "call_count": int(row[1]),
                        "cost": float(row[2] or 0),
                    })

                return {
                    "year": year,
                    "month": month,
                    "total_cost": round(total_cost, 4),
                    "total_calls": total_calls,
                    "by_type": by_type,
                    "daily": daily,
                }
        except Exception as e:
            print(f"Failed to get monthly cost: {e}")
            return {
                "year": year,
                "month": month,
                "total_cost": 0,
                "total_calls": 0,
                "by_type": [],
                "daily": [],
            }

    def get_user_cost(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """
        获取指定用户的成本统计

        Args:
            user_id: 用户ID
            days: 统计天数

        Returns:
            用户成本统计字典
        """
        start_time = datetime.now() - timedelta(days=days)

        try:
            with get_db_session() as session:
                result = session.execute(
                    text("""
                        SELECT
                            analysis_type,
                            COUNT(*) as call_count,
                            SUM(input_tokens) as total_input_tokens,
                            SUM(output_tokens) as total_output_tokens,
                            SUM(total_cost) as total_cost
                        FROM ai_cost_log
                        WHERE user_id = :user_id AND created_at >= :start_time
                        GROUP BY analysis_type
                    """),
                    {"user_id": user_id, "start_time": start_time}
                )

                by_type = []
                total_cost = 0
                total_calls = 0

                for row in result.fetchall():
                    type_cost = float(row[4] or 0)
                    type_calls = int(row[1] or 0)
                    by_type.append({
                        "analysis_type": row[0],
                        "call_count": type_calls,
                        "total_cost": type_cost,
                    })
                    total_cost += type_cost
                    total_calls += type_calls

                return {
                    "user_id": user_id,
                    "period_days": days,
                    "total_cost": round(total_cost, 4),
                    "total_calls": total_calls,
                    "by_type": by_type,
                }
        except Exception as e:
            print(f"Failed to get user cost: {e}")
            return {
                "user_id": user_id,
                "period_days": days,
                "total_cost": 0,
                "total_calls": 0,
                "by_type": [],
            }

    def get_cost_summary(self) -> Dict[str, Any]:
        """
        获取成本汇总（用于后台运营面板）

        Returns:
            成本汇总字典
        """
        today = datetime.now()
        this_month_start = datetime(today.year, today.month, 1)
        yesterday_start = (today - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        # 今日成本
        today_cost = self.get_daily_cost(today)

        # 昨日成本
        yesterday_cost = self.get_daily_cost(yesterday_start)

        # 本月成本
        monthly_cost = self.get_monthly_cost()

        # 估算毛利（假设售价为成本的3倍）
        gross_profit_rate = 0.67  # 67%毛利率
        monthly_revenue = monthly_cost["total_cost"] / (1 - gross_profit_rate) if monthly_cost["total_cost"] > 0 else 0
        monthly_profit = monthly_revenue - monthly_cost["total_cost"]

        return {
            "today": today_cost,
            "yesterday": yesterday_cost,
            "this_month": monthly_cost,
            "estimated_revenue": round(monthly_revenue, 2),
            "estimated_profit": round(monthly_profit, 2),
            "gross_profit_rate": gross_profit_rate,
        }


# 全局单例
_cost_statistics_service: Optional[CostStatisticsService] = None


def get_cost_statistics_service() -> CostStatisticsService:
    """获取成本统计服务单例"""
    global _cost_statistics_service
    if _cost_statistics_service is None:
        _cost_statistics_service = CostStatisticsService()
    return _cost_statistics_service
