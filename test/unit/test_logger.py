import logging
import os
import tempfile
from pathlib import Path
from src.utils.logger import setup_logger, get_logger

def test_setup_logger_creates_log_file():
    """测试日志文件创建"""
    with tempfile.TemporaryDirectory() as temp_dir:
        log_file = os.path.join(temp_dir, 'test.log')
        logger = setup_logger('test', log_file)

        logger.info("Test message")

        # Flush all handlers to ensure content is written
        for handler in logger.handlers:
            handler.flush()

        assert Path(log_file).exists()

        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'Test message' in content

        # Clean up handlers to release file lock
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

def test_logger_format_includes_timestamp():
    """测试日志格式包含时间戳"""
    with tempfile.TemporaryDirectory() as temp_dir:
        log_file = os.path.join(temp_dir, 'test.log')
        logger = setup_logger('test_format', log_file)

        logger.info("Test message")

        # Flush all handlers to ensure content is written
        for handler in logger.handlers:
            handler.flush()

        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # 检查时间戳格式 [2026-07-11 14:30:00]
            assert len(content) > 20  # 包含时间戳

        # Clean up handlers to release file lock
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

def test_get_logger_returns_singleton():
    """测试获取日志器单例"""
    logger1 = get_logger('test')
    logger2 = get_logger('test')

    assert logger1 is logger2

def test_file_handler_configuration():
    """测试文件处理器配置"""
    with tempfile.TemporaryDirectory() as temp_dir:
        log_file = os.path.join(temp_dir, 'test.log')
        logger = setup_logger('test', log_file)

        # 验证文件处理器级别为INFO
        # 通过检查handlers来验证
        assert len(logger.handlers) == 2  # 一个文件处理器，一个控制台处理器
        file_handler = [h for h in logger.handlers if isinstance(h, logging.FileHandler)][0]
        console_handler = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)][0]

        assert file_handler.level == logging.INFO
        assert console_handler.level == logging.INFO

        # Clean up handlers to release file lock
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

def test_singleton_behavior():
    """测试单例行为"""
    with tempfile.TemporaryDirectory() as temp_dir:
        log_file = os.path.join(temp_dir, 'test.log')
        logger1 = get_logger('test', log_file=log_file)
        logger2 = get_logger('test', log_file=log_file)

        # 应该返回同一个实例
        assert logger1 is logger2

def test_rotates_when_file_exceeds_size_limit():
    """单文件超过大小上限时应滚动出新文件"""
    import time as _time
    from src.utils.logger import DailySizeRotatingHandler

    with tempfile.TemporaryDirectory() as temp_dir:
        log_file = os.path.join(temp_dir, 'test.log')
        handler = DailySizeRotatingHandler(log_file, max_bytes=500, backup_days=7)
        logger = logging.getLogger('test_size_rotation')
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        try:
            for _ in range(20):
                logger.info('x' * 100)

            rotated = [f for f in os.listdir(temp_dir) if f.startswith('test.log.')]
            assert len(rotated) >= 1  # 至少滚动出一个历史文件
            assert os.path.exists(log_file)  # 主文件仍在继续写入
        finally:
            logger.removeHandler(handler)
            handler.close()

def test_deletes_files_older_than_retention_days():
    """超过保留天数的历史日志文件应被自动删除"""
    import time as _time
    from src.utils.logger import DailySizeRotatingHandler

    with tempfile.TemporaryDirectory() as temp_dir:
        log_file = os.path.join(temp_dir, 'test.log')

        # 伪造历史滚动日志：8天前的应删除，1天前的应保留
        old_file = os.path.join(temp_dir, 'test.log.2026-08-30_080000')
        with open(old_file, 'w', encoding='utf-8') as f:
            f.write('old log')
        recent_file = os.path.join(temp_dir, 'test.log.2026-09-07_080000')
        with open(recent_file, 'w', encoding='utf-8') as f:
            f.write('recent log')

        eight_days_ago = _time.time() - 8 * 86400
        one_day_ago = _time.time() - 1 * 86400
        os.utime(old_file, (eight_days_ago, eight_days_ago))
        os.utime(recent_file, (one_day_ago, one_day_ago))

        handler = DailySizeRotatingHandler(log_file, backup_days=7)
        logger = logging.getLogger('test_retention')
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        try:
            # 强制触发跨天滚动，带动过期清理
            handler.rolloverAt = int(_time.time()) - 1
            logger.info('trigger rollover')

            assert not os.path.exists(old_file), '超过7天的日志应被删除'
            assert os.path.exists(recent_file), '7天内的日志应保留'
        finally:
            logger.removeHandler(handler)
            handler.close()

def test_default_rotation_limits():
    """默认滚动上限：单文件50MB、保留7天"""
    from src.utils.logger import get_file_handler, DEFAULT_MAX_BYTES, DEFAULT_BACKUP_DAYS

    assert DEFAULT_MAX_BYTES == 50 * 1024 * 1024
    assert DEFAULT_BACKUP_DAYS == 7

    with tempfile.TemporaryDirectory() as temp_dir:
        log_file = os.path.join(temp_dir, 'test.log')
        handler = get_file_handler(log_file)
        try:
            assert handler.max_bytes == DEFAULT_MAX_BYTES
            assert handler.backup_days == DEFAULT_BACKUP_DAYS
        finally:
            handler.close()

def test_same_path_loggers_share_one_file_handler():
    """不同日志器写同一路径时应共享同一个滚动文件处理器"""
    from src.utils.logger import get_file_handler

    with tempfile.TemporaryDirectory() as temp_dir:
        log_file = os.path.join(temp_dir, 'test.log')
        handler1 = get_file_handler(log_file)
        handler2 = get_file_handler(log_file)
        assert handler1 is handler2

        logger_a = setup_logger('mod_a', log_file)
        logger_b = setup_logger('mod_b', log_file)
        fh_a = [h for h in logger_a.handlers if isinstance(h, logging.FileHandler)][0]
        fh_b = [h for h in logger_b.handlers if isinstance(h, logging.FileHandler)][0]
        assert fh_a is fh_b

        logger_a.removeHandler(fh_a)
        logger_b.removeHandler(fh_b)
        handler1.close()
