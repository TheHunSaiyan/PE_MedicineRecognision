from pathlib import Path

class AppConfig:
    CONFIG_FILE = "camera_params.json"
    CALI_CONFIG_FILE = "camera_calibration_params.json"
    CAPTURED_IMAGES_DIR = "CapturedImages"
    CALIBRATION_IMAGES_DIR = "CalibrationImages"
    UNDISTORTED_IMAGES_DIR = "UndistortedImages"
    PILLS_DATA_FILE = "Pills.json"
    
    @classmethod
    def ensure_directories_exist(cls):
        Path(cls.CAPTURED_IMAGES_DIR).mkdir(exist_ok=True)
        Path(cls.CALIBRATION_IMAGES_DIR).mkdir(exist_ok=True)
        Path(cls.UNDISTORTED_IMAGES_DIR).mkdir(exist_ok=True)