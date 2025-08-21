import cv2
import numpy as np
import os

from typing import Dict

from Logger.logger import logger


class CreateMask:
    @staticmethod
    def process_data(img_files: str, txt_files: str, scale_factor: int = 4):
        """
        Given the file paths to an image file and a corresponding text file with object coordinates in YOLO format,
        loads the image, extracts the object coordinates, interpolates them, and creates a binary mask indicating where
        the object is.

        Args:
            img_files: A string specifying the path to an image file.
            txt_files: A string specifying the path to a text file with YOLO object coordinates.
            scale_factor:

        Returns:
            A numpy array representing a binary mask indicating the object location.
            Returns None if either file path is invalid.
        """

        try:
            img = cv2.imread(img_files)
        except FileNotFoundError:
            logger.error(f"{img_files} is not a valid image file.")
            return None

        height, width = img.shape[:2]

        big_mask = np.zeros(
            (height * scale_factor, width * scale_factor), dtype=np.uint8)

        with open(txt_files, "r") as f:
            lines = f.readlines()

        for line in lines:
            parts = line.strip().split()
            coords = list(map(float, parts[1:]))
            polygon = []

            for i in range(0, len(coords), 2):
                x = int(round(coords[i] * width * scale_factor))
                y = int(round(coords[i + 1] * height * scale_factor))
                polygon.append((x, y))

            polygon_np = np.array([polygon], dtype=np.int32)
            cv2.fillPoly(big_mask, polygon_np, 255)

        mask = cv2.resize(big_mask, (width, height),
                          interpolation=cv2.INTER_AREA)

        return mask

    @staticmethod
    def save_masks(mask: np.ndarray, img_file: str, path_to_files: Dict[str, str]) -> None:
        """
        This function saves the mask to a given path.

        Args:
            mask: Mask image.
            img_file: path of the image file.
            path_to_files: path to the files.

        Returns:
            None
        """

        name = os.path.basename(img_file)
        save_path = os.path.join(path_to_files, name)
        cv2.imwrite(save_path, mask)
