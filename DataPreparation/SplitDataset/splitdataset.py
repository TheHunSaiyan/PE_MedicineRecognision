import os
import random
import shutil

import cv2
from fastapi import HTTPException, status
from math import floor
import numpy as np
import redis
import pickle
from pydantic import BaseModel
from typing import Dict, List, Tuple

from Config.config import AppConfig
from Logger.logger import logger

class SplitDataset:
    def __init__(self):
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
    
    async def get_data_availability(self):
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
        
        redis_mask_count = len(self.redis.keys(f"{self.mask_cache_prefix}*"))
        total_mask_count = max(mask_count, redis_mask_count)
        
        valid_mask_count = 0
        if mask_count > 0:
            for mask_file in os.listdir(AppConfig.ORIGINAL_MASKS):
                mask_path = os.path.join(AppConfig.ORIGINAL_MASKS, mask_file)
                if is_valid_mask(mask_path):
                    valid_mask_count += 1
        
        valid_mask_count = max(valid_mask_count, redis_mask_count)
        
        if (total_mask_count == 0 or valid_mask_count != img_count or 
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
        keys = self.redis.keys(f"{self.mask_cache_prefix}*")
        if keys:
            self.redis.delete(*keys)
        logger.info("Cleared mask cache")
        
    def serialize_mask(self, mask: np.ndarray) -> bytes:
        return pickle.dumps(mask)
    
    def deserialize_mask(self, mask_bytes: bytes) -> np.ndarray:
        return pickle.loads(mask_bytes)
    
    async def generate_masks_from_labels(self):
        os.makedirs(AppConfig.ORIGINAL_MASKS, exist_ok=True)
        
        for img_file in os.listdir(AppConfig.ORIGINAL_IMAGES):
            img_path = os.path.join(AppConfig.ORIGINAL_IMAGES, img_file)
            base_name = os.path.splitext(img_file)[0]
            cache_key = f"{self.mask_cache_prefix}{base_name}"
            
            cached_mask = self.redis.get(cache_key)
            if cached_mask:
                mask = self.deserialize_mask(cached_mask)
                mask_path = os.path.join(AppConfig.ORIGINAL_MASKS, f"{base_name}.jpg")
                cv2.imwrite(mask_path, mask)
                logger.info(f"Loaded mask from cache: {base_name}")
                continue
                
            img = cv2.imread(img_path)
            if img is None:
                continue
                
            height, width = img.shape[:2]
            mask = np.zeros((height, width), dtype=np.uint8)
            
            label_file = f"{base_name}.txt"
            label_path = os.path.join(AppConfig.ORIGINAL_LABELS, label_file)
            
            if not os.path.exists(label_path):
                continue
                
            with open(label_path, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) < 5:
                        continue
                        
                    class_id = int(parts[0])
                    points = list(map(float, parts[1:]))
                    
                    polygon = []
                    for i in range(0, len(points), 2):
                        x = int(points[i] * width)
                        y = int(points[i+1] * height)
                        polygon.append([x, y])
                    
                    cv2.fillPoly(mask, [np.array(polygon)], color=255)
            
            self.redis.set(cache_key, self.serialize_mask(mask), ex=86400)
            
            mask_path = os.path.join(AppConfig.ORIGINAL_MASKS, f"{base_name}.jpg")
            cv2.imwrite(mask_path, mask)
            logger.info(f"Generated and cached mask: {base_name}")
        
    def start_split(self, data: Dict[str, any]):
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
            
            image_files = [f for f in os.listdir(image_dir) if f.endswith('.jpg')]
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
                
                u_images = [f for f in os.listdir(image_dir) if f.endswith('.jpg') and '_u_' in f]
                s_images = [f for f in os.listdir(image_dir) if f.endswith('.jpg') and '_s_' in f]
                
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
                val_images = u_images[train_u:train_u+val_u] + s_images[train_s:train_s+val_s]
                test_images = u_images[train_u+val_u:] + s_images[train_s+val_s:]
                
                random.shuffle(train_images)
                random.shuffle(val_images)
                random.shuffle(test_images)
                
                self._total_files = (len(train_images) + len(val_images) + len(test_images)) * 3
            
            self.move_files(train_images, image_dir, seg_label_dir, mask_dir, split_dirs['train'])
            self.move_files(val_images, image_dir, seg_label_dir, mask_dir, split_dirs['val'])
            self.move_files(test_images, image_dir, seg_label_dir, mask_dir, split_dirs['test'])
            
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
        for split in split_dirs.values():
            for dir_path in split.values():
                for item in os.listdir(dir_path):
                    item_path = os.path.join(dir_path, item)
                    if os.path.isfile(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
    
    def group_by_class(self, image_files: List[str]) -> Dict[str, List[str]]:
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
        for img_file in image_files:
            
            if self._total_files == 1 and self._processed_files == 0:
                break
            
            shutil.copy(
                os.path.join(src_img_dir, img_file),
                os.path.join(dest_dirs['images'], img_file)
            )
            self._processed_files += 1
            self._progress = int((self._processed_files / self._total_files) * 100)
            
            label_file = os.path.splitext(img_file)[0] + '.txt'
            shutil.copy(
                os.path.join(src_label_dir, label_file),
                os.path.join(dest_dirs['labels'], label_file)
            )
            
            self._processed_files += 1
            self._progress = int((self._processed_files / self._total_files) * 100)
            
            shutil.copy(
                os.path.join(src_mask_dir, img_file),
                os.path.join(dest_dirs['masks'], img_file)
            )
            
            self._processed_files += 1
            self._progress = int((self._processed_files / self._total_files) * 100)
            
    async def stop_split(self):
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
                        logger.warning(f"Could not delete {file_path}: {str(e)}")
                        if attempt == max_retries - 1:
                            raise
                return
            except Exception as e:
                raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error during stop: {str(e)}"
            )