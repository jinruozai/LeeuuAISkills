import logging
import os

def get_logger(name: str, log_level: int = logging.INFO) -> logging.Logger:
    """获取配置好的 logger 实例
    
    Args:
        name: logger 名称
        log_level: 日志级别，默认为 INFO
        
    Returns:
        配置好的 logger 实例
    """
    # 创建 logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # 避免重复添加 handler
    if not logger.handlers:
        # 创建 console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        
        # 创建 formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        
        # 添加 handler
        logger.addHandler(console_handler)
    
    return logger