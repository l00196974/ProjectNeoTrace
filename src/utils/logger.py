"""日志工具模块"""
import sys
from pathlib import Path
from loguru import logger
from src.utils.config import Config


def setup_logger(name: str = "neotrace", log_file: str = None):
    """
    配置日志记录器

    Args:
        name: 日志记录器名称
        log_file: 日志文件名（可选）
    """
    # 移除默认的 handler
    logger.remove()

    # 添加控制台输出
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=Config.LOG_LEVEL,
        colorize=True,
    )

    # 添加文件输出
    if log_file:
        log_path = Config.LOG_DIR / log_file
        logger.add(
            log_path,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=Config.LOG_LEVEL,
            rotation="100 MB",
            retention="30 days",
            compression="zip",
        )

    return logger


# 创建默认日志记录器
default_logger = setup_logger("neotrace", "neotrace.log")
