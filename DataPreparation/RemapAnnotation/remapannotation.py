import json
import os
import re
import shutil

from fastapi import UploadFile, HTTPException, status
from typing import Dict, List

from Config.config import AppConfig
from Logger.logger import logger


class RemapAnnotation:
    def __init__(self):
        """
        Initialize the RemapAnnotation class.

        Args:
            None

        Returns:
            None
        """
        self.current_file_index = 0
        self.total_files = 0
        self.files_to_process: List[str] = []
        self.processing = False
        self.data = None

    async def load_medication_data(self):
        """
        Load medication data from the configured JSON file.

        Args:
            None

        Returns:
            None
        """
        json_file = AppConfig.PILLS_DATA_FILE
        with open(json_file, 'r') as file:
            self.data = json.load(file)

    def _find_real_id(self, class_name: str) -> int:
        """
        Find the real ID corresponding to a class name from the loaded medication data.

        Args:
            class_name (str): The class name to find the corresponding ID for.

        Returns:
            int: The real ID corresponding to the class name, or 0 if not found.
        """
        if not self.data:
            logger.error("Medication data can't be loaded.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Medication data can't be loaded."
            )

        for med in self.data.get('medications', []):
            if med.get('name') == class_name:
                return med.get('id')

        logger.error(f"Class name '{class_name}' not found in JSON data.")
        return 0

    async def _process_file(self, file_path: str, mode: str):
        """
        Process a single file to remap annotations based on the specified mode.

        Args:
            file_path (str): The path to the file to be processed.
            mode (str): The mode of processing ('objectdetection' or 'segmentation').

        Returns:
            None
        """
        filename = os.path.basename(file_path)
        class_name = os.path.basename(filename)
        match = re.match(
            r'^(?:[0-3]\d{3})_([a-z0-9_-]+)_(?:u|s)_(?:t|b)\.txt$', filename.lower())

        if not match:
            logger.error(
                f"Filename '{class_name}' does not match expected pattern.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Filename '{class_name}' does not match expected pattern.")
            )

        if mode == 'objectdetection':
            class_name = match.group(1)

            real_id = self._find_real_id(class_name)
        else:
            real_id = 0

        with open(file_path, 'r') as file:
            lines = file.readlines()

        new_lines = []
        for line in lines:
            parts = line.strip().split()
            if not parts:
                continue
            parts[0] = str(int(real_id))
            new_line = " ".join(parts)
            new_lines.append(new_line)

        with open(file_path, 'w') as file:
            for line in new_lines:
                file.write(line + "\n")

    async def _clean_output_directory(self):
        """
        Clean the output directory by removing existing files and creating a new directory.

        Args:
            None

        Returns:
            bool: True if the output directory was cleaned successfully, False otherwise.
        """
        try:
            if os.path.exists(AppConfig.REMAPED_ANNOTATION):
                shutil.rmtree(AppConfig.REMAPED_ANNOTATION)
            os.makedirs(AppConfig.REMAPED_ANNOTATION, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Error cleaning output directory: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(f"Error cleaning output directory: {str(e)}")
            )

    async def start_remap(self, files: List[UploadFile], mode: str):
        """
        Start the remapping process for the provided files based on the specified mode.

        Args:
            files (List[UploadFile]): List of files to be processed.
            mode (str): The mode of processing ('objectdetection' or 'segmentation').

        Returns:
            Dict[str, Any]: A dictionary indicating the status and message of the operation.
        """
        try:
            if self.processing:
                return {"status": "error", "message": "Process already running"}
            await self.load_medication_data()

            await self._clean_output_directory()

            os.makedirs(AppConfig.REMAPED_ANNOTATION, exist_ok=True)

            self.files_to_process = []
            if mode is None:
                logger.error("Mode is required for remapping")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Mode is required for remapping"
                )

            if mode not in ['objectdetection', 'segmentation']:
                logger.error(f"Invalid mode: {mode}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid mode: {mode}"
                )

            for file in files:
                clean_filename = os.path.basename(file.filename)
                file_path = os.path.join(
                    AppConfig.REMAPED_ANNOTATION, clean_filename)
                with open(file_path, 'wb') as f:
                    f.write(await file.read())
                self.files_to_process.append(file_path)

            self.total_files = len(self.files_to_process)
            self.current_file_index = 0
            self.processing = True

            logger.info(f"Starting remap annotation with mode: {mode}")
            if mode == 'objectdetection':
                logger.info("Processing files for Object Detection mode")
            elif mode == 'segmentation':
                logger.info("Processing files for Segmentation mode")

            for i, file_path in enumerate(self.files_to_process):
                try:
                    await self._process_file(file_path, mode)
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {str(e)}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=(f"Error processing {file_path}: {str(e)}")
                    )
                finally:
                    self.current_file_index = i + 1
        except Exception as e:
            logger.error(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(e)
            )

        self.processing = False
        return {"status": "success", "message": f"Processed {self.total_files} files"}

    async def get_progress(self) -> Dict[str, float]:
        """
        Get the current progress of the remapping process.

        Args:
            None

        Returns:
            Dict[str, float]: A dictionary containing the progress percentage and file counts.
        """
        if not self.processing:
            return {
                "progress": 100,
                "processed": self.total_files,
                "total": self.total_files
            }

        if self.total_files == 0:
            return {"progress": 0, "processed": 0, "total": 0}

        progress = (self.current_file_index / self.total_files) * 100
        return {
            "progress": progress,
            "processed": self.current_file_index,
            "total": self.total_files
        }
