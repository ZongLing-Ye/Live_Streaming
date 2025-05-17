import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logging(name='live_assistant'):
    # 创建logs目录（如果不存在）
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 获取根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 如果根日志记录器已经有处理器，先清除
    if root_logger.handlers:
        root_logger.handlers.clear()

    # 创建格式化器
    # 为不同类型的日志使用不同的格式
    standard_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 添加控制台处理器到根日志记录器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(standard_formatter)
    root_logger.addHandler(console_handler)

    # 添加主日志文件处理器
    main_file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    main_file_handler.setFormatter(standard_formatter)
    root_logger.addHandler(main_file_handler)

    # 设置第三方库的日志级别
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('gradio').setLevel(logging.WARNING)
    logging.getLogger('websockets').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('sounddevice').setLevel(logging.WARNING)  # 添加sounddevice的日志级别控制
    logging.getLogger('soundfile').setLevel(logging.WARNING)    # 添加soundfile的日志级别控制

    # 创建并返回指定名称的日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 不添加处理器，让它使用根日志记录器的处理器
    logger.propagate = True

    return logger

# 创建默认的全局logger
default_logger = setup_logging() 