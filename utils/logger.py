"""
日志管理模块 - 只记录ERROR级别日志
"""
import logging
import os
import sys


def setup_logger(log_file=None, log_level=logging.ERROR):
    """
    设置日志记录器
    
    Args:
        log_file: 日志文件路径，如果为None则使用配置文件的路径
        log_level: 日志级别，默认为ERROR
    
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    logger = logging.getLogger('company_report_scraper')
    logger.setLevel(log_level)
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 创建日志文件目录（使用os.path避免Path对象的编码转换问题）
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
    
    # 文件handler（使用UTF-8编码）
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, encoding='utf-8', errors='replace')
        except Exception:
            # 如果文件路径编码有问题，尝试使用字符串路径
            file_handler = logging.FileHandler(str(log_file), encoding='utf-8', errors='replace')
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # 创建一个过滤器，确保所有消息都是UTF-8编码
        class SafeEncodingFilter(logging.Filter):
            def filter(self, record):
                # 确保消息是字符串且可以安全编码
                if isinstance(record.msg, str):
                    try:
                        # 尝试编码为UTF-8，如果失败则替换错误字符
                        record.msg = record.msg.encode('utf-8', errors='replace').decode('utf-8')
                    except Exception:
                        # 如果还是失败，转换为ASCII
                        record.msg = record.msg.encode('ascii', errors='replace').decode('ascii')
                return True
        
        file_handler.addFilter(SafeEncodingFilter())
        logger.addHandler(file_handler)
    
    return logger


def get_logger():
    """获取全局日志记录器"""
    return logging.getLogger('company_report_scraper')


def safe_log_error(message, *args, **kwargs):
    """
    安全地记录错误日志，处理编码问题
    
    Args:
        message: 日志消息
        *args: 格式化参数
        **kwargs: 其他参数
    """
    logger = get_logger()
    try:
        # 确保消息是字符串
        if not isinstance(message, str):
            message = str(message)
        
        # 如果有格式化参数，安全地格式化
        if args:
            try:
                message = message % args
            except Exception:
                # 如果格式化失败，使用str格式化
                message = message + " " + " ".join(str(arg) for arg in args)
        
        # 确保消息可以安全编码为UTF-8
        try:
            message.encode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            # 如果编码失败，替换错误字符
            message = message.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
        
        logger.error(message, **kwargs)
    except Exception:
        # 如果所有处理都失败，尝试使用ASCII安全的消息
        try:
            safe_message = str(message).encode('ascii', errors='ignore').decode('ascii')
            if safe_message:
                logger.error(safe_message)
        except:
            pass  # 最后放弃，避免程序崩溃

