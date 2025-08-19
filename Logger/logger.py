import datetime
import logging
from pathlib import Path

from Config.config import AppConfig


class Logger:
    def __init__(self):
        """
        Initialize the Logger instance.
        Sets up the logging directory, creates a timestamped log file,
        and configures the basic logging settings with file handler.

        Args:
            None

        Returns:
            None
        """
        self.log_path = Path(AppConfig.LOG)
        self.log_path.mkdir(parents=True, exist_ok=True)

        launch_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = self.log_path / f"log_{launch_time}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def info(self, message: str):
        """
        Log an informational message.

        Args:
            message (str): The informational message to log.

        Returns:
            None
        """
        self.logger.info(message)

    def warning(self, message: str):
        """
        Log a warning message.

        Args:
            message (str): The warning message to log.

        Returns:
            None
        """
        self.logger.warning(message)

    def error(self, message: str):
        """
        Log an error message.

        Args:
            message (str): The error message to log.

        Returns:
            None
        """
        self.logger.error(message)

    def log(self, message: str):
        """
        Log a general message (alias for info level).

        Args:
            message (str): The message to log at INFO level.

        Returns:
            None
        """
        self.logger.info(message)


logger = Logger()
