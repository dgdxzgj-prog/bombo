"""
日志工具模块
"""
import sys
import os
from loguru import logger

from src.config import settings


def safe_str(s, max_len: int = 50, encoding_errors: str = "replace") -> str:
    """
    安全字符串处理，用于日志输出

    Args:
        s: 输入字符串
        max_len: 最大长度，超出部分截断
        encoding_errors: 编码错误处理方式

    Returns:
        处理后的安全字符串
    """
    if s is None:
        return ""

    # 确保是字符串
    if not isinstance(s, str):
        s = str(s)

    # 移除或替换可能导致编码问题的字符
    # 只保留可打印的 ASCII 和合法 Unicode 字符
    try:
        s.encode("utf-8")
    except UnicodeEncodeError:
        s = s.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")

    # 截断
    if len(s) > max_len:
        s = s[:max_len] + "..."

    return s


def safe_print(msg: str) -> None:
    """
    安全的打印函数，处理 Windows GBK 编码问题

    Args:
        msg: 要打印的消息
    """
    try:
        # 尝试用 UTF-8 编码后输出
        print(msg)
    except UnicodeEncodeError:
        # 如果失败，用 ignore 模式处理后打印
        try:
            encoded = msg.encode(sys.stdout.encoding or "utf-8", errors="ignore")
            print(encoded.decode(sys.stdout.encoding or "utf-8", errors="ignore"))
        except Exception:
            # 最后保底：只打印 ASCII 字符
            ascii_msg = msg.encode("ascii", errors="ignore").decode("ascii", errors="ignore")
            print(ascii_msg)


def setup_logger() -> None:
    """配置日志"""
    logger.remove()

    # 设置环境变量以支持更好的编码处理
    if sys.platform == "win32":
        os.environ["PYTHONIOENCODING"] = "utf-8"

    # 控制台输出
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL,
        colorize=True,
        enqueue=True,  # 线程安全
    )

    # 文件输出
    logger.add(
        "logs/bombo.log",
        rotation="500 MB",
        retention="10 days",
        level=settings.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        encoding="utf-8",
    )


# 初始化logger
setup_logger()

__all__ = ["logger", "safe_str", "safe_print"]
