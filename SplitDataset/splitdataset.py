import os
import random
import shutil

from fastapi import HTTPException, status
from typing import Dict, List, Tuple

from config import AppConfig
from logger import logger

class SplitDataset:
    
    async def get_data_availability(self):
        return {
            "images": os.path.exists(AppConfig.DATASET_IMAGES) and bool(os.listdir(AppConfig.DATASET_IMAGES)),
            "segmentation_labels": os.path.exists(AppConfig.DATASET_LABELS) and bool(os.listdir(AppConfig.DATASET_LABELS)),
            "mask_images": os.path.exists(AppConfig.DATASET_MASKS) and bool(os.listdir(AppConfig.DATASET_MASKS))
        }
        
    async def start_split(self, data: Dict[str, any]):
        try:
            train_pct = data.get('train')
            val_pct = data.get('val')
            test_pct = data.get('test')
            segregated = data.get('segregated')
            
            image_dir = AppConfig.DATASET_IMAGES
            seg_label_dir = AppConfig.DATASET_LABELS
            mask_dir = AppConfig.DATASET_MASKS
            
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
            
            self._clear_split_directories(split_dirs)
            
            image_files = [f for f in os.listdir(image_dir) if f.endswith('.jpg')]
            
            if segregated:
                class_images = self._group_by_class(image_files)
                train_images, val_images, test_images = self._split_by_class(
                    class_images, train_pct, val_pct, test_pct)
            else:
                random.shuffle(image_files)
                total = len(image_files)
                train_end = int(total * train_pct / 100)
                val_end = train_end + int(total * val_pct / 100)
                
                train_images = image_files[:train_end]
                val_images = image_files[train_end:val_end]
                test_images = image_files[val_end:]
            
            self._move_files(train_images, image_dir, seg_label_dir, mask_dir, split_dirs['train'])
            self._move_files(val_images, image_dir, seg_label_dir, mask_dir, split_dirs['val'])
            self._move_files(test_images, image_dir, seg_label_dir, mask_dir, split_dirs['test'])
            
            logger.info("Successfull split.")
            return {
                "status": "success",
                "train_count": len(train_images),
                "val_count": len(val_images),
                "test_count": len(test_images),
                "segregated": segregated
            }
            
        except Exception as e:
            logger.error(f"Error during dataset split: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error during dataset split: {str(e)}"
            )
    
    def _clear_split_directories(self, split_dirs: Dict[str, Dict[str, str]]):
        for split in split_dirs.values():
            for dir_path in split.values():
                for item in os.listdir(dir_path):
                    item_path = os.path.join(dir_path, item)
                    if os.path.isfile(item_path):
                        os.unlink(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
    
    def _group_by_class(self, image_files: List[str]) -> Dict[str, List[str]]:
        class_images = {}
        for filename in image_files:
            parts = filename.split('_')
            class_name = '_'.join(parts[:-1])
            
            if class_name not in class_images:
                class_images[class_name] = []
            class_images[class_name].append(filename)
        return class_images
    
    def _split_by_class(self, class_images: Dict[str, List[str]], 
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
    
    def _move_files(self, image_files: List[str], 
                   src_img_dir: str, src_label_dir: str, src_mask_dir: str,
                   dest_dirs: Dict[str, str]):
        for img_file in image_files:
            shutil.copy(
                os.path.join(src_img_dir, img_file),
                os.path.join(dest_dirs['images'], img_file)
            )
            
            label_file = os.path.splitext(img_file)[0] + '.txt'
            shutil.copy(
                os.path.join(src_label_dir, label_file),
                os.path.join(dest_dirs['labels'], label_file)
            )
            
            shutil.copy(
                os.path.join(src_mask_dir, img_file),
                os.path.join(dest_dirs['masks'], img_file)
            )