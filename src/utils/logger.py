import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

# 日志器单例存储
_loggers = {}

def setup_logger(name: str, log_file: str, level: str = 'INFO') -> logging.Logger:
    """
    设置日志器

    Args:
        name: 日志器名称
        log_file: 日志文件路径
        level: 日志级别

    Returns:
        配置好的日志器
    """
    # 创建日志目录
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # 创建或获取日志器
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # 避免重复添加处理器
    if logger.handlers:
        return logger

    # 创建格式化器
    formatter = logging.Formatter(
        '[%(levelname)s] [%(asctime)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

def get_logger(name: str = 'baidu-download',
               log_file: Optional[str] = None,
               level: str = 'INFO') -> logging.Logger:
    """
    获取日志器单例

    Args:
        name: 日志器名称
        log_file: 日志文件路径
        level: 日志级别

    Returns:
        日志器实例
    """
    if name not in _loggers:
        if log_file is None:
            log_file = './logs/app.log'
        _loggers[name] = setup_logger(name, log_file, level)

    return _loggers[name]
