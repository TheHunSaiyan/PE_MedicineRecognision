import datetime
import logging
from pathlib import Path

from config import AppConfig

class Logger:
    def __init__(self):
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
        self.logger.info(message)
    
    def warning(self, message: str):
        self.logger.warning(message)
    
    def error(self, message: str):
        self.logger.error(message)
        
    def log(self, message: str):
        self.logger.info(message)

logger = Logger()