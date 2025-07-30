import os
import json
import random
import shutil
import threading
from typing import Dict, List

from fastapi import HTTPException, status

from Config.config import AppConfig
from Logger.logger import logger

class KFoldSort:
    def __init__(self):
        self.progress = {
            "progress": 0,
            "processed": 0,
            "total": 0,
            "status": "idle"
        }
        self.lock = threading.Lock()
        self.kfold_data = {}

        self.k_fold_dir = AppConfig.K_FOLD
        self.data_list_file = AppConfig.DATA_LIST_JSON
        self.source_dir = AppConfig.CONSUMER_STREAM_IMAGES
        self.train_output_dir = AppConfig.K_FOLD_TRAIN
        self.test_output_dir = AppConfig.K_FOLD_TEST
        self.subfolders = ["rgb", "texture", "contour", "lbp"]

    def start_sorting(self, data: Dict):
        mode = data.get("mode")
        num_folds = int(data.get("num_folds", 5))
        selected_fold = data.get("selected_fold", "fold1")
        erase = data.get("erase", False)

        logger.info("Starting sort...")

        with self.lock:
            self.progress = {
                "progress": 0,
                "processed": 0,
                "total": 0,
                "status": "running"
            }

        if erase:
            self.erase_existing()

        if mode == "new":
            self.kfold_data = self.generate_folds(num_folds)
        elif mode == "exists":
            self.kfold_data = self.load_folds()
        else:
            logger.error("Invalid mode.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Invalid mode."
            )

        if selected_fold not in self.kfold_data:
            logger.error("Selected fold '{selected_fold}' not found.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Selected fold '{selected_fold}' not found."
            )
            
        train_classes = [
            cls
            for fold_name, class_list in self.kfold_data.items()
            if fold_name != selected_fold
            for cls in class_list
        ]
        test_classes = self.kfold_data[selected_fold]
        all_classes = list(set(train_classes + test_classes))

        with self.lock:
            self.progress["total"] = len(all_classes) * len(self.subfolders)

        for class_name in all_classes:
            is_test = class_name in test_classes
            self.copy_class_images(class_name, test=is_test)

            with self.lock:
                self.progress["processed"] += len(self.subfolders)
                self.progress["progress"] = int((self.progress["processed"] / self.progress["total"]) * 100)

        with self.lock:
            self.progress["status"] = "done"

    async def get_sort_progress(self) -> Dict:
        with self.lock:
            logger.info(self.progress)
            return self.progress

    def generate_folds(self, num_folds: int) -> Dict[str, List[str]]:
        try:
            with open(self.data_list_file, 'r') as f:
                data = json.load(f)
                class_list = [
                    pill["name"].split("-")[-1].strip().lower()
                    for pill in data.get("medications", [])
                    if pill["name"].split("-")[-1].strip().lower() != "multi"
                ]
        except Exception as e:
            logger.error("Failed to load medication list: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to load medication list: {e}"
            )
        random.shuffle(class_list)
        folds = {f"fold{i + 1}": [] for i in range(num_folds)}

        for i, cls in enumerate(class_list):
            folds[f"fold{(i % num_folds) + 1}"].append(cls)

        os.makedirs(self.k_fold_dir, exist_ok=True)
        file_path = os.path.join(self.k_fold_dir, "kfolds.txt")

        with open(file_path, "w") as f:
            for fold_name, class_names in folds.items():
                f.write(f"{fold_name}: {', '.join(class_names)}\n")

        return folds

    def load_folds(self) -> Dict[str, List[str]]:
        file_path = os.path.join(self.k_fold_dir, "kfolds.txt")
        if not os.path.exists(file_path):
            logger.error("No saved fold file found.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"No saved fold file found."
            )
        folds = {}
        with open(file_path, "r") as f:
            for line in f:
                if ":" in line:
                    fold_name, class_names = line.strip().split(":")
                    folds[fold_name.strip()] = [
                        cls.strip().lower() for cls in class_names.strip().split(",") if cls.strip()
                    ]
        return folds

    def erase_existing(self):
        for path in [self.train_output_dir, self.test_output_dir]:
            for sub in self.subfolders:
                full_path = os.path.join(path, sub)
                if os.path.exists(full_path):
                    shutil.rmtree(full_path)
                os.makedirs(full_path, exist_ok=True)

    def copy_class_images(self, class_name: str, test: bool = False):
        dst_root = self.test_output_dir if test else self.train_output_dir

        for sub in self.subfolders:
            src_subfolder = os.path.join(self.source_dir, sub)
            dst_class_folder = os.path.join(dst_root, sub, class_name)

            if not os.path.exists(src_subfolder):
                continue

            os.makedirs(dst_class_folder, exist_ok=True)

            for file_name in os.listdir(src_subfolder):
                if not file_name.lower().startswith(class_name.lower()):
                    continue

                src_file = os.path.join(src_subfolder, file_name)
                dst_file = os.path.join(dst_class_folder, file_name)

                if os.path.isfile(src_file):
                    shutil.copyfile(src_file, dst_file)
