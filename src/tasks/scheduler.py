"""
定时任务调度器
管理三类定时任务（均为 interval 间隔执行）：
1. 新视频发现任务 (每6小时)
2. 每小时统一调度任务（快照采集 + 爆款判定 + 状态更新）
3. 每日热榜采集任务 (每小时)

使用 threading.Timer 实现简单定时调度
"""
from datetime import datetime, time
from typing import Optional, Callable, Dict, List
from dataclasses import dataclass, field
from threading import Timer
import time as time_module


@dataclass
class TaskResult:
    """任务执行结果"""
    task_name: str
    success: bool
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    message: str = ""
    error: Optional[str] = None


@dataclass
class ScheduledTask:
    """定时任务定义"""
    task_id: str
    name: str
    func: Callable
    interval_seconds: Optional[int] = None  # 间隔执行
    cron_hour: Optional[int] = None         # 定时执行-小时
    cron_minute: Optional[int] = None       # 定时执行-分钟
    cron_day_of_week: Optional[str] = None  # 定时执行-星期
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


class SimpleScheduler:
    """简单定时任务调度器（无外部依赖）"""

    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self._timers: Dict[str, Timer] = {}
        self._running = False

    def add_interval_task(
        self,
        task_id: str,
        name: str,
        func: Callable,
        interval_seconds: int
    ) -> None:
        """添加间隔执行任务"""
        self.tasks[task_id] = ScheduledTask(
            task_id=task_id,
            name=name,
            func=func,
            interval_seconds=interval_seconds,
        )

    def add_cron_task(
        self,
        task_id: str,
        name: str,
        func: Callable,
        hour: int,
        minute: int,
        day_of_week: Optional[str] = None
    ) -> None:
        """添加定时执行任务"""
        self.tasks[task_id] = ScheduledTask(
            task_id=task_id,
            name=name,
            func=func,
            cron_hour=hour,
            cron_minute=minute,
            cron_day_of_week=day_of_week,
        )

    def remove_task(self, task_id: str) -> None:
        """移除任务"""
        if task_id in self._timers:
            self._timers[task_id].cancel()
            del self._timers[task_id]
        if task_id in self.tasks:
            del self.tasks[task_id]

    def start(self) -> None:
        """启动调度器"""
        if self._running:
            return
        self._running = True
        self._schedule_all()

    def stop(self) -> None:
        """停止调度器"""
        self._running = False
        for timer in self._timers.values():
            timer.cancel()
        self._timers.clear()

    def _schedule_all(self) -> None:
        """调度所有任务"""
        for task_id, task in self.tasks.items():
            if task.enabled:
                self._schedule_task(task)

    def _schedule_task(self, task: ScheduledTask) -> None:
        """调度单个任务"""
        if task.interval_seconds:
            # 间隔任务
            delay = task.interval_seconds
        else:
            # 定时任务 - 计算到下一个执行时间的时间
            delay = self._calculate_cron_delay(task)
            if delay <= 0:
                delay = 86400  # 如果已过执行时间，等待一天

        timer = Timer(delay, self._execute_task, args=[task.task_id])
        timer.daemon = True
        self._timers[task.task_id] = timer
        timer.start()

    def _calculate_cron_delay(self, task: ScheduledTask) -> float:
        """计算定时任务的延迟秒数"""
        now = datetime.now()
        target = datetime.combine(now.date(), time(task.cron_hour, task.cron_minute))

        if target <= now:
            target = target.replace(day=now.day + 1)

        return (target - now).total_seconds()

    def _execute_task(self, task_id: str) -> None:
        """执行任务"""
        if not self._running or task_id not in self.tasks:
            return

        task = self.tasks[task_id]
        task.last_run = datetime.now()

        try:
            task.func()
        except Exception as e:
            print(f"Task {task_id} failed: {e}")

        # 重新调度
        if self._running and task.enabled:
            self._schedule_task(task)

    def run_task_now(self, task_id: str) -> TaskResult:
        """立即执行任务"""
        if task_id not in self.tasks:
            return TaskResult(
                task_name=task_id,
                success=False,
                started_at=datetime.now(),
                error="Task not found",
            )

        task = self.tasks[task_id]
        result = TaskResult(task_name=task_id, success=False, started_at=datetime.now())

        try:
            task.func()
            result.success = True
            result.message = f"{task_id} executed successfully"
        except Exception as e:
            result.error = str(e)
            result.message = f"{task_id} failed: {e}"
        finally:
            result.finished_at = datetime.now()
            result.duration_seconds = (result.finished_at - result.started_at).total_seconds()

        return result

    def get_status(self) -> dict:
        """获取调度器状态"""
        return {
            "running": self._running,
            "tasks": [
                {
                    "id": t.task_id,
                    "name": t.name,
                    "enabled": t.enabled,
                    "interval": t.interval_seconds,
                    "cron": f"{t.cron_hour}:{t.cron_minute}" if t.cron_hour is not None else None,
                    "last_run": t.last_run.isoformat() if t.last_run else None,
                }
                for t in self.tasks.values()
            ],
        }


# 为了兼容性，保留TaskScheduler作为别名
TaskScheduler = SimpleScheduler


# 全局调度器实例
_scheduler: Optional[SimpleScheduler] = None


def get_scheduler() -> SimpleScheduler:
    """获取调度器单例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = SimpleScheduler()
    return _scheduler
