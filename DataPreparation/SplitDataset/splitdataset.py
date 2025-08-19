import cv2
import numpy as np
import os
import random
import redis
import pickle
import shutil


from fastapi import HTTPException, status
from math import floor
from PIL import Image, ImageDraw, ImageFilter
from pydantic import BaseModel
from scipy.interpolate import splprep, splev
from typing import Dict, List, Tuple

from Config.config import AppConfig
from Logger.logger import logger


class SplitDataset:
    def __init__(self):
        """
        Initialize the SplitDataset class.

        Args:
            None

        Returns:
            None
        """
        self._progress = 0
        self._total_files = 0
        self._processed_files = 0
        self.redis = redis.Redis(
            host='redis',
            port=AppConfig.REDIS_PORT,
            db=2,
            decode_responses=False
        )
        self.mask_cache_prefix = "mask_gen:"

    async def get_progress(self):
        """
        Get the current progress of the dataset splitting process.

        Args:
            None

        Returns:
            Dict[str, float]: A dictionary containing the progress percentage and file counts.
        """
        logger.info({
            "progress": self._progress,
            "processed": self._processed_files,
            "total": self._total_files
        })
        return {
            "progress": self._progress,
            "processed": self._processed_files,
            "total": self._total_files
        }

    def clear_mask_cache(self):
        """
        Clear the mask cache in Redis.

        Args:
            None

        Returns:
            None
        """
        keys = self.redis.keys(f"{self.mask_cache_prefix}*")
        if keys:
            self.redis.delete(*keys)
        logger.info("Cleared mask cache")

    async def get_data_availability(self):
        """
        Check the availability of original images, segmentation labels, and mask images.
        If masks are missing or invalid, generate them from labels.

        Args:
            None

        Returns:
            Dict[str, bool]: A dictionary indicating the availability of each data type.
        """
        logger.info("Checking data availability...")

        def get_file_count(path):
            return len([f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]) if os.path.exists(path) else 0

        def is_valid_mask(mask_path):
            try:
                base_name = os.path.splitext(os.path.basename(mask_path))[0]
                cache_key = f"{self.mask_cache_prefix}{base_name}"

                if self.redis.exists(cache_key):
                    return True

                mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
                if mask is None:
                    return False
                return set(np.unique(mask)).issubset({0, 255})
            except Exception as e:
                logger.error(f"Error validating mask {mask_path}: {str(e)}")
                return False

        img_count = get_file_count(AppConfig.ORIGINAL_IMAGES)
        label_count = get_file_count(AppConfig.ORIGINAL_LABELS)
        mask_count = get_file_count(AppConfig.ORIGINAL_MASKS)
        print(
            f"Image count: {img_count}, Label count: {label_count}, Mask count: {mask_count}")

        self.clear_mask_cache()

        valid_mask_count = 0
        if mask_count > 0:
            for mask_file in os.listdir(AppConfig.ORIGINAL_MASKS):
                mask_path = os.path.join(AppConfig.ORIGINAL_MASKS, mask_file)
                if is_valid_mask(mask_path):
                    valid_mask_count += 1

        if (mask_count == 0 or valid_mask_count != img_count or
                valid_mask_count != label_count) and img_count > 0 and label_count > 0:
            logger.info("Missing or invalid masks found, generating masks...")
            await self.generate_masks_from_labels()
            valid_mask_count = img_count

        counts_equal = len({img_count, label_count, valid_mask_count}) == 1

        return {
            "images": img_count > 0 and counts_equal,
            "segmentation_labels": label_count > 0 and counts_equal,
            "mask_images": valid_mask_count > 0 and counts_equal
        }

    def clear_mask_cache(self):
        """ 
        Clear the mask cache in Redis.

        Args:
            None

        Returns:
            None
        """
        keys = self.redis.keys(f"{self.mask_cache_prefix}*")
        if keys:
            self.redis.delete(*keys)
        logger.info("Cleared mask cache")

    def serialize_mask(self, mask: np.ndarray) -> bytes:
        """
        Serialize a mask array to bytes for storage in Redis.

        Args:
            mask (np.ndarray): The mask array to serialize.

        Returns:
            bytes: The serialized mask.
        """
        return pickle.dumps(mask)

    def deserialize_mask(self, mask_bytes: bytes) -> np.ndarray:
        """
        Deserialize a mask from bytes back to a numpy array.

        Args:
            mask_bytes (bytes): The serialized mask bytes.

        Returns:
            np.ndarray: The deserialized mask array.
        """
        return pickle.loads(mask_bytes)

    async def generate_masks_from_labels(self, interp_points: int = 100):
        """
        Generate masks from segmentation labels and cache them in Redis.

        Args:
            interp_points (int): Number of interpolation points for smoothing the mask.

        Returns:
            None
        """
        os.makedirs(AppConfig.ORIGINAL_MASKS, exist_ok=True)

        for img_file in os.listdir(AppConfig.ORIGINAL_IMAGES):
            img_path = os.path.join(AppConfig.ORIGINAL_IMAGES, img_file)
            base_name = os.path.splitext(img_file)[0]
            cache_key = f"{self.mask_cache_prefix}{base_name}"

            cached_mask = self.redis.get(cache_key)
            if cached_mask:
                mask = self.deserialize_mask(cached_mask)
                mask_path = os.path.join(
                    AppConfig.ORIGINAL_MASKS, f"{base_name}.jpg")
                cv2.imwrite(mask_path, mask)
                logger.info(f"Loaded mask from cache: {base_name}")
                continue

            label_file = f"{base_name}.txt"
            label_path = os.path.join(AppConfig.ORIGINAL_LABELS, label_file)

            if not os.path.exists(label_path):
                continue

            try:
                with Image.open(img_path) as img:
                    img_width, img_height = img.size

                with open(label_path, "r") as file:
                    lines = file.readlines()

                mask = Image.new('L', (img_width, img_height), 0)
                draw = ImageDraw.Draw(mask)

                for line in lines:
                    parts = line.strip().split()
                    if len(parts) < 5:
                        continue

                    class_id = int(parts[0])
                    yolo_coords = [float(x) for x in parts[1:]]

                    coords = []
                    for i, coord in enumerate(yolo_coords):
                        if i % 2 == 0:
                            coords.append(coord * img_width)
                        else:
                            coords.append(coord * img_height)
                    coords = np.array(coords).reshape(-1, 2)

                    if len(coords) > 3:
                        x, y = coords[:, 0], coords[:, 1]
                        tck, _ = splprep([x, y], s=0, per=True)
                        u_new = np.linspace(0, 1, interp_points)
                        x_new, y_new = splev(u_new, tck)
                        coords_interp = list(zip(x_new, y_new))
                    else:
                        coords_interp = coords.tolist()

                    draw.polygon(coords_interp, outline=255, fill=255)

                mask = mask.filter(ImageFilter.GaussianBlur(radius=2))
                mask_array = (np.array(mask) > 0).astype(np.uint8) * 255

                self.redis.set(cache_key, self.serialize_mask(
                    mask_array), ex=86400)

                mask_path = os.path.join(
                    AppConfig.ORIGINAL_MASKS, f"{base_name}.jpg")
                cv2.imwrite(mask_path, mask_array)
                logger.info(f"Generated and cached mask: {base_name}")

            except Exception as e:
                logger.error(f"Error processing {img_file}: {str(e)}")
                continue

    def start_split(self, data: Dict[str, any]):
        """
        Start the dataset splitting process based on the provided configuration.

        Args:
            data (Dict[str, any]): A dictionary containing the split percentages and whether to segregate by class.

        Returns:
            Dict[str, any]: A dictionary containing the status and counts of the split datasets.
        """
        logger.info("Spliting dataset started...")
        self._progress = 0
        self._processed_files = 0
        self._total_files = 0

        try:
            train_pct = data.get('train')
            val_pct = data.get('val')
            test_pct = data.get('test')
            segregated = data.get('segregated')

            image_dir = AppConfig.ORIGINAL_IMAGES
            seg_label_dir = AppConfig.ORIGINAL_LABELS
            mask_dir = AppConfig.ORIGINAL_MASKS

            if not all([
                os.path.exists(image_dir) and os.listdir(image_dir),
                os.path.exists(seg_label_dir) and os.listdir(seg_label_dir),
                os.path.exists(mask_dir) and os.listdir(mask_dir)
            ]):
                logger.error("Required directories are missing or empty")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Required directories are missing or empty"
                )

            split_dirs = {
                'train': {
                    'images': os.path.join(AppConfig.SPLIT_DATASET, 'train', 'images'),
                    'labels': os.path.join(AppConfig.SPLIT_DATASET, 'train', 'labels'),
                    'masks': os.path.join(AppConfig.SPLIT_DATASET, 'train', 'masks')
                },
                'val': {
                    'images': os.path.join(AppConfig.SPLIT_DATASET, 'val', 'images'),
                    'labels': os.path.join(AppConfig.SPLIT_DATASET, 'val', 'labels'),
                    'masks': os.path.join(AppConfig.SPLIT_DATASET, 'val', 'masks')
                },
                'test': {
                    'images': os.path.join(AppConfig.SPLIT_DATASET, 'test', 'images'),
                    'labels': os.path.join(AppConfig.SPLIT_DATASET, 'test', 'labels'),
                    'masks': os.path.join(AppConfig.SPLIT_DATASET, 'test', 'masks')
                }
            }

            for split in split_dirs.values():
                for dir_path in split.values():
                    os.makedirs(dir_path, exist_ok=True)

            self.clear_split_directories(split_dirs)

            image_files = [f for f in os.listdir(
                image_dir) if f.endswith('.jpg')]
            self._total_files = len(image_files) * 3

            if segregated:
                class_images = self.group_by_class(image_files)
                train_images, val_images, test_images = self.split_by_class(
                    class_images, train_pct, val_pct, test_pct)
            else:
                random.shuffle(image_files)
                total = len(image_files)
                train_end = int(total * train_pct / 100)
                val_end = train_end + int(total * val_pct / 100)

                train_images = image_files[:train_end]
                val_images = image_files[train_end:val_end]
                test_images = image_files[val_end:]

                u_images = [f for f in os.listdir(
                    image_dir) if f.endswith('.jpg') and '_u_' in f]
                s_images = [f for f in os.listdir(
                    image_dir) if f.endswith('.jpg') and '_s_' in f]

                random.shuffle(u_images)
                random.shuffle(s_images)

                total_u = len(u_images)
                total_s = len(s_images)

                train_u = floor(total_u * train_pct / 100)
                val_u = floor(total_u * val_pct / 100)
                test_u = total_u - train_u - val_u

                train_s = floor(total_s * train_pct / 100)
                val_s = floor(total_s * val_pct / 100)
                test_s = total_s - train_s - val_s

                train_images = u_images[:train_u] + s_images[:train_s]
                val_images = u_images[train_u:train_u +
                                      val_u] + s_images[train_s:train_s+val_s]
                test_images = u_images[train_u+val_u:] + \
                    s_images[train_s+val_s:]

                random.shuffle(train_images)
                random.shuffle(val_images)
                random.shuffle(test_images)

                self._total_files = (len(train_images) +
                                     len(val_images) + len(test_images)) * 3

            self.move_files(train_images, image_dir,
                            seg_label_dir, mask_dir, split_dirs['train'])
            self.move_files(val_images, image_dir, seg_label_dir,
                            mask_dir, split_dirs['val'])
            self.move_files(test_images, image_dir,
                            seg_label_dir, mask_dir, split_dirs['test'])

            logger.info("Successfull split.")
            return {
                "status": "success",
                "train_count": len(train_images),
                "val_count": len(val_images),
                "test_count": len(test_images),
                "segregated": segregated
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error during dataset split: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error during dataset split: {str(e)}"
            )

    def clear_split_directories(self, split_dirs: Dict[str, Dict[str, str]]):
        """
        Clear the contents of the split dataset directories.

        Args:
            split_dirs (Dict[str, Dict[str, str]]): A dictionary containing paths to the split directories.

        Returns:
            None
        """
        for split in split_dirs.values():
            for dir_path in split.values():
                for item in os.listdir(dir_path):
                    item_path = os.path.join(dir_path, item)
                    if os.path.isfile(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)

    def group_by_class(self, image_files: List[str]) -> Dict[str, List[str]]:
        """
        Group image files by their class based on the naming convention.

        Args:
            image_files (List[str]): List of image filenames.

        Returns:
            Dict[str, List[str]]: A dictionary where keys are class names and values are lists of filenames.
        """
        class_images = {}
        for filename in image_files:
            parts = filename.split('_')
            class_name = '_'.join(parts[:-1])

            if class_name not in class_images:
                class_images[class_name] = []
            class_images[class_name].append(filename)
        return class_images

    def split_by_class(self, class_images: Dict[str, List[str]],
                       train_pct: int, val_pct: int, test_pct: int) -> Tuple[List[str], List[str], List[str]]:
        """
        Split images by class into training, validation, and test sets based on the specified percentages.

        Args:
            class_images (Dict[str, List[str]]): A dictionary where keys are class names and values are lists of filenames.
            train_pct (int): Percentage of images to include in the training set.
            val_pct (int): Percentage of images to include in the validation set.
            test_pct (int): Percentage of images to include in the test set.

        Returns:
            Tuple[List[str], List[str], List[str]]: Lists of filenames for training, validation, and test sets.
        """
        train_images = []
        val_images = []
        test_images = []

        for class_name, images in class_images.items():
            random.shuffle(images)
            total = len(images)
            train_end = int(total * train_pct / 100)
            val_end = train_end + int(total * val_pct / 100)

            train_images.extend(images[:train_end])
            val_images.extend(images[train_end:val_end])
            test_images.extend(images[val_end:])

        return train_images, val_images, test_images

    def move_files(self, image_files: List[str],
                   src_img_dir: str, src_label_dir: str, src_mask_dir: str,
                   dest_dirs: Dict[str, str]):
        """
        Move image, label, and mask files to the specified destination directories.

        Args:
            image_files (List[str]): List of image filenames to move.
            src_img_dir (str): Source directory for images.
            src_label_dir (str): Source directory for labels.
            src_mask_dir (str): Source directory for masks.
            dest_dirs (Dict[str, str]): Dictionary containing destination directories for images, labels, and masks.

        Returns:
            None
        """
        for img_file in image_files:

            if self._total_files == 1 and self._processed_files == 0:
                break

            shutil.copy(
                os.path.join(src_img_dir, img_file),
                os.path.join(dest_dirs['images'], img_file)
            )
            self._processed_files += 1
            self._progress = int(
                (self._processed_files / self._total_files) * 100)

            label_file = os.path.splitext(img_file)[0] + '.txt'
            shutil.copy(
                os.path.join(src_label_dir, label_file),
                os.path.join(dest_dirs['labels'], label_file)
            )

            self._processed_files += 1
            self._progress = int(
                (self._processed_files / self._total_files) * 100)

            shutil.copy(
                os.path.join(src_mask_dir, img_file),
                os.path.join(dest_dirs['masks'], img_file)
            )

            self._processed_files += 1
            self._progress = int(
                (self._processed_files / self._total_files) * 100)

    async def stop_split(self):
        """
        Stop the dataset splitting process and clear the contents of the split directories.

        Args:
            None

        Returns:
            Dict[str, str]: A dictionary indicating the status and message of the operation.
        """
        self._progress = 0
        self._processed_files = 0
        self._total_files = 1

        split_dirs = {
            'train': {
                'images': os.path.join(AppConfig.SPLIT_DATASET, 'train', 'images'),
                'labels': os.path.join(AppConfig.SPLIT_DATASET, 'train', 'labels'),
                'masks': os.path.join(AppConfig.SPLIT_DATASET, 'train', 'masks')
            },
            'val': {
                'images': os.path.join(AppConfig.SPLIT_DATASET, 'val', 'images'),
                'labels': os.path.join(AppConfig.SPLIT_DATASET, 'val', 'labels'),
                'masks': os.path.join(AppConfig.SPLIT_DATASET, 'val', 'masks')
            },
            'test': {
                'images': os.path.join(AppConfig.SPLIT_DATASET, 'test', 'images'),
                'labels': os.path.join(AppConfig.SPLIT_DATASET, 'test', 'labels'),
                'masks': os.path.join(AppConfig.SPLIT_DATASET, 'test', 'masks')
            }
        }

        try:
            for split in split_dirs.values():
                for dir_path in split.values():
                    if os.path.exists(dir_path):
                        self.clear_directory_contents(dir_path)

            return {"status": "stopped", "message": "Split operation stopped and directory contents cleared"}
        except Exception as e:
            logger.error(f"Error during stop: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error during stop: {str(e)}"
            )

    def clear_directory_contents(self, dir_path: str):
        """
        Clear the contents of a directory.

        Args:
            dir_path (str): The path to the directory to clear.

        Returns:
            None
        """
        max_retries = 3

        for attempt in range(max_retries):
            try:
                for filename in os.listdir(dir_path):
                    file_path = os.path.join(dir_path, filename)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        logger.warning(
                            f"Could not delete {file_path}: {str(e)}")
                        if attempt == max_retries - 1:
                            raise
                return
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error during stop: {str(e)}"
                )
