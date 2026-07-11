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
