import logging
import os
import time
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional

# 滚动日志默认配置：单文件最大50MB，最多保留7天
DEFAULT_MAX_BYTES = 50 * 1024 * 1024
DEFAULT_BACKUP_DAYS = 7

# 日志器单例存储
_loggers = {}
# 文件处理器缓存：同一日志文件全局共享一个滚动处理器，避免多个handler各自滚动互相冲突
_file_handlers = {}
_console_handler = None

class DailySizeRotatingHandler(TimedRotatingFileHandler):
    """
    按天滚动并限制单文件大小的日志处理器

    - 每天凌晨0点滚动一次
    - 单文件写入达到 max_bytes 时立即滚动（后缀精确到秒，同一天多次滚动不会互相覆盖）
    - 自动删除修改时间超过 backup_days 的历史日志文件
    """

    def __init__(self, filename, when='midnight',
                 max_bytes: int = DEFAULT_MAX_BYTES,
                 backup_days: int = DEFAULT_BACKUP_DAYS,
                 encoding: str = 'utf-8'):
        self.max_bytes = max_bytes
        self.backup_days = backup_days
        self._suffix_fmt = '%Y-%m-%d_%H%M%S'
        # backupCount=0：禁用父类按数量清理，统一改用按天清理
        super().__init__(filename, when=when, backupCount=0, encoding=encoding)
        # 启动时顺带清理一次历史遗留的过期日志
        self.cleanup_expired_files()

    def shouldRollover(self, record) -> int:
        # 单文件大小达到上限：立即滚动
        if self.max_bytes > 0:
            if self.stream is None:
                self.stream = self._open()
            self.stream.seek(0, 2)
            msg = "%s\n" % self.format(record)
            if self.stream.tell() + len(msg) >= self.max_bytes:
                return 1
        # 跨天：按时间滚动
        return super().shouldRollover(record)

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None

        # 用当前时间生成精确到秒的滚动后缀
        suffix = time.strftime(self._suffix_fmt, time.localtime(int(time.time())))
        target = f"{self.baseFilename}.{suffix}"
        seq = 1
        while os.path.exists(target):
            target = f"{self.baseFilename}.{suffix}.{seq}"
            seq += 1

        if os.path.exists(self.baseFilename):
            try:
                os.rename(self.baseFilename, target)
            except OSError:
                # 文件被其他进程占用时放弃本次重命名，继续写主文件
                pass

        self.cleanup_expired_files()

        if not self.delay:
            self.stream = self._open()

        # 重新计算下一个按天滚动时间点
        current_time = int(time.time())
        new_rollover_at = self.computeRollover(current_time)
        while new_rollover_at <= current_time:
            new_rollover_at += self.interval
        self.rolloverAt = new_rollover_at

    def cleanup_expired_files(self):
        """删除修改时间超过 backup_days 的历史日志文件"""
        if self.backup_days <= 0:
            return
        cutoff = time.time() - self.backup_days * 86400
        log_dir = os.path.dirname(self.baseFilename) or '.'
        base_name = os.path.basename(self.baseFilename)
        try:
            names = os.listdir(log_dir)
        except OSError:
            return
        for name in names:
            if not name.startswith(base_name + '.'):
                continue
            path = os.path.join(log_dir, name)
            try:
                if os.path.getmtime(path) < cutoff:
                    os.remove(path)
            except OSError:
                continue

def get_file_handler(log_file: str) -> logging.Handler:
    """
    获取指定日志文件的共享滚动文件处理器

    同一路径只创建一个处理器，多处复用不会产生多份滚动副本

    Args:
        log_file: 日志文件路径

    Returns:
        滚动文件处理器
    """
    key = os.path.abspath(log_file)
    handler = _file_handlers.get(key)
    # 已关闭的处理器（stream为None）不可复用，需重建
    if handler is not None and getattr(handler, 'stream', None) is not None:
        return handler

    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    handler = DailySizeRotatingHandler(log_file)
    _file_handlers[key] = handler
    return handler

def _get_console_handler() -> logging.Handler:
    """获取共享的控制台处理器"""
    global _console_handler
    if _console_handler is None:
        _console_handler = logging.StreamHandler()
    return _console_handler

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

    # 文件处理器（按天+按大小滚动，共享实例）- 使用配置的日志级别
    file_handler = get_file_handler(log_file)
    file_handler.setLevel(getattr(logging, level.upper()))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 控制台处理器 - 使用配置的日志级别
    console_handler = _get_console_handler()
    console_handler.setLevel(getattr(logging, level.upper()))
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
