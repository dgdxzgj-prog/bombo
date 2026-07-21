"""
反爬策略模块
"""
import random
import time
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class AntiCrawlerConfig:
    """反爬配置"""
    user_agents: List[str] = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0",
    ])
    min_delay: float = 2.0   # 最小延时(秒)
    max_delay: float = 6.0   # 最大延时(秒)
    max_retries: int = 3     # 最大重试次数
    proxy_pool: Optional[List[str]] = None  # 代理IP池
    default_proxy: Optional[str] = None  # 默认代理（None表示不使用代理）


class AntiCrawlerManager:
    """反爬策略管理器"""

    def __init__(self, config: Optional[AntiCrawlerConfig] = None):
        self.config = config or AntiCrawlerConfig()
        self._current_proxy: Optional[str] = None

    def get_random_user_agent(self) -> str:
        """获取随机User-Agent"""
        return random.choice(self.config.user_agents)

    def get_random_delay(self) -> float:
        """获取随机延时"""
        return random.uniform(self.config.min_delay, self.config.max_delay)

    def apply_delay(self) -> None:
        """应用随机延时"""
        delay = self.get_random_delay()
        time.sleep(delay)

    def get_random_proxy(self) -> Optional[str]:
        """获取随机代理IP"""
        if self.config.proxy_pool:
            proxy = random.choice(self.config.proxy_pool)
            self._current_proxy = proxy
            return proxy
        elif self.config.default_proxy and not self.config.proxy_pool:
            # 只有在没有配置代理池时才使用默认代理
            self._current_proxy = self.config.default_proxy
            return self.config.default_proxy
        return None

    def get_headers(self) -> dict:
        """获取随机Headers"""
        return {
            "User-Agent": self.get_random_user_agent(),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.bilibili.com",
            "Origin": "https://www.bilibili.com",
        }

    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """判断是否应该重试"""
        if attempt >= self.config.max_retries:
            return False

        # 网络异常、超时、限流等情况应该重试
        retry_exceptions = (
            "timeout",
            "Connection",
            "429",
            "403",
            "ProxyError",
        )
        error_msg = str(exception).lower()
        return any(keyword in error_msg for keyword in retry_exceptions)


# 全局反爬管理器实例
_anti_crawler: Optional[AntiCrawlerManager] = None


def get_anti_crawler() -> AntiCrawlerManager:
    """获取反爬管理器单例"""
    global _anti_crawler
    if _anti_crawler is None:
        _anti_crawler = AntiCrawlerManager()
    return _anti_crawler


def set_anti_crawler(manager: AntiCrawlerManager) -> None:
    """设置反爬管理器"""
    global _anti_crawler
    _anti_crawler = manager
