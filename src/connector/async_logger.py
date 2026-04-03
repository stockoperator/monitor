import atexit
import logging
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from queue import Queue


def null_logger() -> logging.Logger:
    logger = logging.getLogger("null")
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    logger.propagate = False
    return logger


def make_async_logger(
    name: str = "app",
    log_file: str = "app.log",
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3,
    level: int = logging.INFO,
) -> logging.Logger:
    log_queue: Queue[logging.LogRecord] = Queue()

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    queue_handler = QueueHandler(log_queue)
    logger.addHandler(queue_handler)

    rotating_handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    rotating_handler.setFormatter(formatter)

    listener = QueueListener(log_queue, rotating_handler, respect_handler_level=True)
    listener.start()
    atexit.register(listener.stop)

    return logger
