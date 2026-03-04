import logging
import logging.handlers
from queue import Queue
import threading


class AsyncLogger(logging.Logger):
    def __init__(self, log_file: str = "app.log", max_bytes: int = 5 * 1024 * 1024, backup_count: int = 3) -> None:
        super().__init__("AsyncLogger", logging.INFO)  # Initialize the base Logger class

        self.log_queue: Queue[str] = Queue()  # Create a queue for logs
        self.queue_handler = logging.handlers.QueueHandler(self.log_queue)  # Set up QueueHandler for logging to the queue
        self.addHandler(self.queue_handler)  # Add the queue handler to the logger

        self.rotating_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")  # Formatter for the handler
        self.rotating_handler.setFormatter(formatter)

        # Create and start the log listener thread
        self.listener_thread = threading.Thread(target=self._listener_thread)
        self.listener_thread.daemon = True  # The thread will end when the program ends
        self.listener_thread.start()

    def _listener_thread(self):
        """Function that listens to the queue and writes logs to the file with rotation."""
        listener = logging.handlers.QueueListener(self.log_queue, self.rotating_handler)
        listener.start()  # Start the listener
