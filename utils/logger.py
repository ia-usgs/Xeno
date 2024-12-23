import os
import datetime
import traceback


class Logger:
    def __init__(self, log_file, log_level="INFO"):
        """
        Initialize the Logger class.

        Parameters:
            log_file (str): The path to the log file where messages will be saved.
            log_level (str, optional): The minimum log level for messages to be recorded.
                                       Defaults to "INFO".

        Attributes:
            log_file (str): The path to the log file.
            log_level (int): The numeric value of the minimum log level.
        """

        self.log_file = log_file
        self.log_level = self._get_log_level_value(log_level)
        self._ensure_log_directory()

    def _ensure_log_directory(self):
        """
        Ensure that the directory for the log file exists.

        Workflow:
            - Creates the log directory if it does not exist.
            - Creates an empty log file if it does not already exist.
        """

        log_dir = os.path.dirname(self.log_file)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w") as file:
                file.write("")  # Create an empty log file

    def _get_log_level_value(self, log_level):
        """
        Convert a log level string to its corresponding numeric value.

        Parameters:
            log_level (str): The log level string (e.g., "DEBUG", "INFO").

        Returns:
            int: The numeric value of the log level. Defaults to 20 (INFO) if the level is not found.
        """

        levels = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}
        return levels.get(log_level.upper(), 20)  # Default to INFO if not found

    def log(self, message, level="INFO", exc_info=False):
        """
        Log a message with a timestamp and severity level.

        Parameters:
            message (str): The log message to record.
            level (str, optional): The severity level of the log message (e.g., "INFO", "ERROR").
                                   Defaults to "INFO".
            exc_info (bool, optional): Whether to include exception traceback information in the log.
                                       Defaults to False.

        Workflow:
            - Checks if the message's log level meets the minimum log level.
            - Prints the log message to the console.
            - Appends the log message to the log file.
            - If `exc_info` is True, includes the exception traceback in the log file.
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
