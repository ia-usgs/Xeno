import os
import datetime
import traceback


class Logger:
    def __init__(self, log_file, log_level="INFO"):
        self.log_file = log_file
        self.log_level = self._get_log_level_value(log_level)
        self._ensure_log_directory()

    def _ensure_log_directory(self):
        """Ensure the log directory and file exist."""
        log_dir = os.path.dirname(self.log_file)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w") as file:
                file.write("")  # Create an empty log file

    def _get_log_level_value(self, log_level):
        """Convert log level string to a numeric value for comparison."""
        levels = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}
        return levels.get(log_level.upper(), 20)  # Default to INFO if not found

    def log(self, message, level="INFO", exc_info=False):
        """
        Log a message with a timestamp and log level.

        :param message: The log message.
        :param level: The severity level of the log message (e.g., INFO, DEBUG).
        :param exc_info: Whether to include exception information.
        """
        level_value = self._get_log_level_value(level)
        if level_value >= self.log_level:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_message = f"[{timestamp}] [{level}] {message}"
            print(log_message)
            with open(self.log_file, "a") as file:
                file.write(log_message + "\n")
                if exc_info:
                    file.write(traceback.format_exc() + "\n")
