import logging
import logging.handlers
from queue import Queue


def null_logger() -> logging.Logger:
    logger = logging.getLogger("null")
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    logger.propagate = False
    return logger


class AsyncLogger:
    def __init__(
        self,
        name: str = "AsyncLogger",
        log_file: str = "app.log",
        max_bytes: int = 5 * 1024 * 1024,
        backup_count: int = 3,
        level: int = logging.INFO,
    ) -> None:
        self.log_queue: Queue[logging.LogRecord] = Queue()

        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.propagate = False

        self.queue_handler = logging.handlers.QueueHandler(self.log_queue)
        self.logger.addHandler(self.queue_handler)

        self.rotating_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        self.rotating_handler.setFormatter(formatter)

        self.listener = logging.handlers.QueueListener(self.log_queue, self.rotating_handler, respect_handler_level=True)
        self.listener.start()

    def get_logger(self) -> logging.Logger:
        return self.logger

    def stop(self) -> None:
        try:
            self.listener.stop()
        except Exception:
            pass
