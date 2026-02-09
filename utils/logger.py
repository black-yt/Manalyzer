import logging
import os
os.makedirs('webui/data', exist_ok=True)

class LogFormatter(logging.Formatter):
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"

    FORMATS = {
        logging.DEBUG: GREEN + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + RESET,
        logging.INFO: CYAN + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + RESET,
        logging.WARNING: YELLOW + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + RESET,
        logging.ERROR: RED + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + RESET,
        logging.CRITICAL: MAGENTA + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + RESET,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, self.FORMATS[logging.INFO])
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

def create_logger(name, log_directory, level='debug'):
    os.makedirs(log_directory, exist_ok=True)

    logger = logging.getLogger(name)
    
    logger.handlers.clear()
    if level == 'debug':
        logger.setLevel(logging.DEBUG)
    elif level == 'info':
        logger.setLevel(logging.INFO)
    elif level == 'warning':
        logger.setLevel(logging.WARNING)
    elif level == 'error':
        logger.setLevel(logging.ERROR)
    elif level == 'critical':
        logger.setLevel(logging.CRITICAL)
    else:
        raise Exception("[create_logger][wrong level]")

    # # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(LogFormatter())
    logger.addHandler(console_handler)

    # 文件输出
    file_handler = logging.FileHandler(os.path.join(log_directory, f'{name}.log'))
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)

    file_handler = logging.FileHandler('webui/data/chat.log')
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)
    return logger


if __name__ == '__main__':
    logger = create_logger('try', 'logs')
    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")
    logger.critical("This is a critical message.")

    logger = create_logger('try', 'logs')
    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")
    logger.critical("This is a critical message.")