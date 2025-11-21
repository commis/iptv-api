import logging
import logging.handlers
import os
from datetime import datetime
from typing import Union


class LoggerFactory:
    """日志工厂，用于创建和配置统一的日志器"""

    LOG_DIR = "logs"
    LOG_FILE = f"app_{datetime.now().strftime('%Y%m%d')}.log"
    DEFAULT_FORMAT = "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    SIMPLE_FORMAT = "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    _root_logger = None

    @staticmethod
    def _create_log_dir() -> None:
        """创建日志目录"""
        if not os.path.exists(LoggerFactory.LOG_DIR):
            os.makedirs(LoggerFactory.LOG_DIR)

    @staticmethod
    def _get_file_handler(
            level: int = logging.INFO,
            backup_days: int = 30,
            log_format: str = DEFAULT_FORMAT
    ) -> logging.Handler:
        """创建按日期分割的文件处理器"""
        LoggerFactory._create_log_dir()

        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=f"{LoggerFactory.LOG_DIR}/{LoggerFactory.LOG_FILE}",
            when="D",
            interval=1,
            backupCount=backup_days,
            encoding="utf-8"
        )

        file_handler.setLevel(level)
        formatter = logging.Formatter(log_format, datefmt=LoggerFactory.DATE_FORMAT)
        file_handler.setFormatter(formatter)
        return file_handler

    @staticmethod
    def _get_console_handler(
            level: int = logging.INFO,
            log_format: str = SIMPLE_FORMAT
    ) -> logging.Handler:
        """创建控制台处理器"""
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        formatter = logging.Formatter(log_format, datefmt=LoggerFactory.DATE_FORMAT)
        console_handler.setFormatter(formatter)
        return console_handler

    @staticmethod
    def get_logger(
            name: str,
            level: Union[str, int] = logging.INFO,
            with_console: bool = True
    ) -> logging.Logger:
        """获取配置好的日志器

        Args:
            name: 日志器名称，建议使用模块名
            level: 日志级别，支持字符串('DEBUG', 'INFO', etc.)或int
            with_console: 是否同时输出到控制台
        """
        # 初始化根日志器（单例模式）
        if LoggerFactory._root_logger is None:
            LoggerFactory._root_logger = logging.getLogger()
            LoggerFactory._root_logger.setLevel(logging.DEBUG)  # 根日志器设为最低级别

            # 添加文件处理器
            file_handler = LoggerFactory._get_file_handler()
            LoggerFactory._root_logger.addHandler(file_handler)

            # 添加控制台处理器
            console_handler = LoggerFactory._get_console_handler()
            LoggerFactory._root_logger.addHandler(console_handler)

        # 将字符串级别转换为int
        if isinstance(level, str):
            level = getattr(logging, level.upper(), logging.INFO)

        # 创建或获取命名日志器
        logger = logging.getLogger(name)
        logger.setLevel(level)

        # 控制是否输出到控制台
        if not with_console:
            # 从命名日志器中移除控制台处理器
            for handler in logger.handlers[:]:
                if isinstance(handler, logging.StreamHandler):
                    logger.removeHandler(handler)

        # 确保日志只通过根日志器处理
        logger.propagate = True

        return logger


# 全局错误日志器
error_logger = LoggerFactory.get_logger("error", logging.ERROR, with_console=False)


# 异常钩子处理
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        import sys
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    error_logger.critical("unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))


import sys

sys.excepthook = handle_exception
