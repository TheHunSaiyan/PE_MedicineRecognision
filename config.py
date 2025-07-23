from pathlib import Path

class AppConfig:
    CONFIG_FILE = "camera_params.json"
    CALI_CONFIG_FILE = "camera_calibration_params.json"
    CAPTURED_IMAGES_DIR = "CapturedImages"
    CALIBRATION_IMAGES_DIR = "CalibrationImages"
    UNDISTORTED_IMAGES_DIR = "UndistortedImages"
    PILLS_DATA_FILE = "Pills.json"
    LOG = "Logs"
    DATASET_IMAGES = "Dataset/images"
    DATASET_LABELS = "Dataset/segmentation_labels"
    DATASET_MASKS = "Dataset/mask_images"
    SPLIT_DATASET = "Split"
    SPLIT_TRAIN_IMAGES = "Split/train/images"
    SPLIT_TRAIN_LABELS = "Split/train/labels"
    SPLIT_TRAIN_MASKS = "Split/train/masks"
    SPLIT_VAL_IMAGES = "Split/val/images"
    SPLIT_VAL_LABELS = "Split/val/labels"
    SPLIT_VAL_MASKS = "Split/val/masks"
    AUG_IMAGES = "Augmentation/images"
    AUG_MASKS = "Augmentation/masks"
    AUG_ANN = "Augmentation/annotation"
    BACKGROUND_IMAGES = "BackGroundImages"
    
    @classmethod
    def ensure_directories_exist(cls):
        Path(cls.CAPTURED_IMAGES_DIR).mkdir(exist_ok=True)
        Path(cls.CALIBRATION_IMAGES_DIR).mkdir(exist_ok=True)
        Path(cls.UNDISTORTED_IMAGES_DIR).mkdir(exist_ok=True)