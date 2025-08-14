import base64
import gc
import os
import glob
import cv2
import numpy as np
import random
import shutil
import qrcode
import redis

from fastapi import HTTPException, status
from PIL import Image
from typing import Dict, Any, Generator, List, Optional, Tuple

from Config.config import AppConfig
from Logger.logger import logger

class AugmentImage:
    def __init__(self, stop_event=None):
        self.train_image_path = AppConfig.SPLIT_TRAIN_IMAGES
        self.train_mask_path = AppConfig.SPLIT_TRAIN_MASKS
        self.train_annotation_path = AppConfig.SPLIT_TRAIN_LABELS
        self.val_image_path = AppConfig.SPLIT_VAL_IMAGES
        self.val_mask_path = AppConfig.SPLIT_VAL_MASKS
        self.val_annotation_path = AppConfig.SPLIT_VAL_LABELS
        
        self.aug_train_img_path = AppConfig.AUG_TRAIN_IMAGES
        self.aug_train_mask_path = AppConfig.AUG_TRAIN_MASKS
        self.aug_train_annotation_path = AppConfig.AUG_TRAIN_ANN
        self.aug_val_img_path = AppConfig.AUG_VAL_IMAGES
        self.aug_val_mask_path = AppConfig.AUG_VAL_MASKS
        self.aug_val_annotation_path = AppConfig.AUG_VAL_ANN
        
        self.backgrounds_path = AppConfig.BACKGROUND_IMAGES
        self.stop_event = stop_event
        self._current_progress = 0
        self._total_files = 0
        self._processed_files = 0
        self.stop = False
        
        self.redis = redis.Redis(
        host='redis', 
        port=6379,
        db=0,       
        socket_connect_timeout=3,
        decode_responses=False  
        )
        self.redis_cache_prefix = "img_aug:"
        
        
        
    def _serialize_image(self, image):
        _, buffer = cv2.imencode('.png', image)
        return base64.b64encode(buffer).decode('utf-8')
    
    def _deserialize_image(self, image_str):
        buffer = base64.b64decode(image_str.encode('utf-8'))
        return cv2.imdecode(np.frombuffer(buffer, np.uint8), -1)
    
    def cache_image_triplet(self, img_file, mask_file, ann_file, is_train=True):
        base_name = os.path.splitext(os.path.basename(img_file))[0]
        cache_key = f"{self.redis_cache_prefix}{base_name}"
        
        image = cv2.imread(img_file)
        mask = cv2.imread(mask_file)
        with open(ann_file, 'r') as f:
            annotation = f.read()
        
        if image is None or mask is None:
            return False
            
        data = {
            'image': self._serialize_image(image),
            'mask': self._serialize_image(mask),
            'annotation': annotation,
            'is_train': str(is_train)
        }
        
        self.redis.hset(cache_key, mapping=data)
        self.redis.expire(cache_key, 3600)
        return True
    
    def get_cached_triplet(self, base_name):
        try:
            cache_key = f"{self.redis_cache_prefix}{base_name}"
            
            if not self.redis.exists(cache_key):
                return None
                
            data = self.redis.hgetall(cache_key)
            
            return {
                'image': self._deserialize_image(data[b'image'].decode()),
                'mask': self._deserialize_image(data[b'mask'].decode()),
                'annotation': data[b'annotation'].decode(),
                'is_train': data[b'is_train'].decode().lower() == 'true'
            }
        except Exception as e:
            logger.error(f"Error in get_cached_triplet: {str(e)}")
            return None
        
    async def get_data_availability(self):
        return {
            "val_images": os.path.exists(AppConfig.SPLIT_VAL_IMAGES) and bool(os.listdir(AppConfig.SPLIT_VAL_IMAGES)),
            "val_segmentation_labels": os.path.exists(AppConfig.SPLIT_VAL_LABELS) and bool(os.listdir(AppConfig.SPLIT_VAL_LABELS)),
            "val_mask_images": os.path.exists(AppConfig.SPLIT_VAL_MASKS) and bool(os.listdir(AppConfig.SPLIT_VAL_MASKS)),
            "train_images": os.path.exists(AppConfig.SPLIT_TRAIN_IMAGES) and bool(os.listdir(AppConfig.SPLIT_TRAIN_IMAGES)),
            "train_segmentation_labels": os.path.exists(AppConfig.SPLIT_TRAIN_LABELS) and bool(os.listdir(AppConfig.SPLIT_TRAIN_LABELS)),
            "train_mask_images": os.path.exists(AppConfig.SPLIT_TRAIN_MASKS) and bool(os.listdir(AppConfig.SPLIT_TRAIN_MASKS))
        }

    def clear_output_directories(self):
        for path in [
            self.aug_train_img_path, self.aug_train_mask_path, self.aug_train_annotation_path,
            self.aug_val_img_path, self.aug_val_mask_path, self.aug_val_annotation_path
        ]:
            if os.path.exists(path):
                for file in os.listdir(path):
                    file_path = os.path.join(path, file)
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        logger.error(f"Failed to delete {file_path}: {e}")
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to delete {file_path}: {e}"
                        )
            else:
                os.makedirs(path, exist_ok=True)

    def save_data(self, image, mask, method, txt_op="copy", txt_file=None, base_name=None, is_train=True, annotation=None):
        if image is None or image.size == 0:
           return
        if mask is None or mask.size == 0:
           return
       
        if is_train:
            img_out_path = os.path.join(self.aug_train_img_path, f"{base_name}.png")
            mask_out_path = os.path.join(self.aug_train_mask_path, f"{base_name}.png")
            ann_out_path = os.path.join(self.aug_train_annotation_path, f"{base_name}.txt")
        else:
            img_out_path = os.path.join(self.aug_val_img_path, f"{base_name}.png")
            mask_out_path = os.path.join(self.aug_val_mask_path, f"{base_name}.png")
            ann_out_path = os.path.join(self.aug_val_annotation_path, f"{base_name}.txt")
        
        os.makedirs(os.path.dirname(img_out_path), exist_ok=True)
        os.makedirs(os.path.dirname(mask_out_path), exist_ok=True)
        os.makedirs(os.path.dirname(ann_out_path), exist_ok=True)
    
        cv2.imwrite(img_out_path, image)
        cv2.imwrite(mask_out_path, mask)
    
        if txt_op == "copy" and txt_file and os.path.exists(txt_file):
            shutil.copy(txt_file, ann_out_path)
        elif annotation:
            with open(ann_out_path, 'w') as f:
                f.write(annotation)
                
        cache_key = f"{self.redis_cache_prefix}aug:{base_name}"
        try:
            self.redis.hset(cache_key, mapping={
                'image': self._serialize_image(image),
                'mask': self._serialize_image(mask),
                'annotation': open(ann_out_path).read(),
                'is_train': str(is_train)
            })
            self.redis.expire(cache_key, 3600)
        except Exception as e:
            logger.error(f"Redis cache error: {str(e)}")
            
    def clear_redis_cache(self):
        cache_keys = self.redis.keys(f"{self.redis_cache_prefix}*")
        if cache_keys:
            self.redis.delete(*cache_keys)

    def _get_file_count(self, path: str) -> int:
        return len(glob.glob(os.path.join(path, "*.jpg"))) + \
               len(glob.glob(os.path.join(path, "*.png"))) + \
               len(glob.glob(os.path.join(path, "*.jpeg")))

    def get_image_triplets(self, is_train: bool) -> Tuple[Generator[Tuple[np.ndarray, np.ndarray, str, bool, str], None, None], int]:
        try:
            self.redis.ping()
        except Exception as e:
            logger.error(f"Redis connection error: {str(e)}")
            return iter([]), 0

        if is_train:
            image_path = self.train_image_path
            mask_path = self.train_mask_path
            annotation_path = self.train_annotation_path
        else:
            image_path = self.val_image_path
            mask_path = self.val_mask_path
            annotation_path = self.val_annotation_path

        file_count = self._get_file_count(image_path)
        if file_count == 0:
            return iter([]), 0

        logger.info(f"Found {file_count} image files in {'train' if is_train else 'val'} set")
        
        def triplet_generator():
            for img_file in glob.glob(os.path.join(image_path, "*.*")):
                if img_file.lower().endswith(('.jpg', '.png', '.jpeg')):
                    base_name = os.path.splitext(os.path.basename(img_file))[0]
                    
                    cached = self.get_cached_triplet(base_name)
                    if cached:
                        yield (cached['image'], cached['mask'], cached['annotation'], cached['is_train'], base_name)
                        continue

                    mask_file = next(
                        (os.path.join(mask_path, f"{base_name}{ext}") 
                        for ext in ['.png', '.jpg', '.jpeg'] 
                        if os.path.exists(os.path.join(mask_path, f"{base_name}{ext}"))))
                    
                    ann_file = next(
                        (os.path.join(annotation_path, f"{base_name}{ext}") 
                         for ext in ['.txt'] 
                         if os.path.exists(os.path.join(annotation_path, f"{base_name}{ext}"))),
                        None)

                    if mask_file and ann_file:
                        if self.cache_image_triplet(img_file, mask_file, ann_file, is_train):
                            image = cv2.imread(img_file)
                            mask = cv2.imread(mask_file)
                            
                            if image is None or mask is None:
                                logger.error(f"Failed to load image/mask pair: {img_file}")
                                continue
                                
                            try:
                                with open(ann_file, 'r') as f:
                                    annotation = f.read()
                                yield (image, mask, annotation, is_train, base_name)
                            except Exception as e:
                                logger.error(f"Error reading annotation {ann_file}: {str(e)}")
                    del image, mask, annotation
                    gc.collect()

        return triplet_generator(), file_count
                    

    def apply_white_balance(self, image):
        scale_factors = np.random.uniform(0.7, 1.2, size=(3,))
        return (image * scale_factors).clip(0, 255).astype(np.uint8)
    
    def apply_blur(self, image):
        ksize = random.choice([3, 5, 7])
        return cv2.GaussianBlur(image, (ksize, ksize), 0)
    
    def apply_brightness(self, image):
        factor = random.uniform(0.6, 1.4)
        return np.clip(image.astype(np.float32) * factor, 0, 255).astype(np.uint8)
    
    def apply_rotation(self, image, mask):
        angle = random.uniform(-45, 45)
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated_image = cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_LINEAR)
        rotated_mask = cv2.warpAffine(mask, matrix, (w, h), flags=cv2.INTER_NEAREST)
        return rotated_image, rotated_mask
    
    def apply_shift(self, image, mask):
        h, w = image.shape[:2]
        dx = random.randint(-w//10, w//10)
        dy = random.randint(-h//10, h//10)
        matrix = np.float32([[1, 0, dx], [0, 1, dy]])
        shifted_img = cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_LINEAR)
        shifted_mask = cv2.warpAffine(mask, matrix, (w, h), flags=cv2.INTER_NEAREST)
        return shifted_img, shifted_mask
    
    def apply_noise(self, image):
        mean = 0
        var = random.uniform(0.001, 0.01)
        sigma = var ** 0.5
        gauss = np.random.normal(mean, sigma, image.shape) * 255
        noisy = image + gauss
        noisy = np.clip(noisy, 0, 255).astype(np.uint8)
        return noisy
    
    def apply_background_change(self, image, mask):
        bg_files = sorted(glob.glob(os.path.join(self.backgrounds_path, "*.*")))
        if not bg_files:
            return image
        background_file = random.choice(bg_files)
        background = cv2.imread(background_file)
        if background is None:
            return image
        background = cv2.resize(background, (image.shape[1], image.shape[0]))
        fg_mask = mask[:, :, 0] > 0
        composite = image.copy()
        composite[~fg_mask] = background[~fg_mask]
        return composite

    def generate_rA9(self):
        while True:
            letter1 = random.choice('abcdefghijklmnopqrstuvwxyz')
            letter2 = random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
            val1 = ord(letter1) - ord('a') + 1
            val2 = ord(letter2) - ord('A') + 1
            number = 28 - (val1 + val2)
            if number > 0:
                return f"{letter1}{letter2}{number}"

    def qr_code(self, image):
        random_code = self.generate_rA9()
        
        qr = qrcode.make(random_code)
        qr = qr.convert("RGB")
        qr = np.array(qr)
        qr = cv2.cvtColor(qr, cv2.COLOR_RGB2BGR)
    
        qr = cv2.resize(qr, (400, 400), interpolation=cv2.INTER_AREA)
    
        h, w = image.shape[:2]
        qr_h, qr_w = qr.shape[:2]
    
        x1 = w - qr_w - 175
        x2 = x1 + qr_w
        y1 = (h // 2) - (qr_h // 2) - 50
        y2 = y1 + qr_h
    
        roi = image[y1:y2, x1:x2]
    
        blended = cv2.addWeighted(roi, 0.3, qr, 0.7, 0)
        image[y1:y2, x1:x2] = blended
        return image

    async def get_progress(self) -> Dict[str, Any]:
        progress = 0
        if self._total_files > 0:
            progress = (self._processed_files / self._total_files) * 100
            
        logger.info({
            "current": self._processed_files,
            "total": self._total_files,
            "progress": progress,
            "status": "Processing" if progress < 100 else "Completed"
        })
        return {
            "current": self._processed_files,
            "total": self._total_files,
            "progress": progress,
            "status": "Processing" if progress < 100 else "Completed"
        }

    def start_augmentation(self, data: Dict[str, Any]) -> Dict[str, str]:
        try:
            self.clear_redis_cache()
            self.clear_output_directories()
            
            self.stop = False
            self._processed_files = 0
            number_of_images = data.get("number_of_images")
            BATCH_SIZE = 10

            train_gen, train_count = self.get_image_triplets(is_train=True)
            val_gen, val_count = self.get_image_triplets(is_train=False)
            
            self._total_files = min(train_count + val_count, number_of_images) if number_of_images else train_count + val_count

            def process_batch(batch: List[Tuple], is_train: bool) -> None:
                for image, mask, annotation, _, base_name in batch:
                    if self.stop:
                        return

                    if data.get("white_balance"):
                        image = self.apply_white_balance(image)
                    if data.get("blur"):
                        image = self.apply_blur(image)
                    if data.get("brightness"):
                        image = self.apply_brightness(image)
                    if data.get("rotate"):
                        image, mask = self.apply_rotation(image, mask)
                    if data.get("shift"):
                        image, mask = self.apply_shift(image, mask)
                    if data.get("noise"):
                        image = self.apply_noise(image)
                    if data.get("change_background"):
                        image = self.apply_background_change(image, mask)
                    if data.get("qr_code"):
                        image = self.qr_code(image)

                    self.save_data(
                        image=image,
                        mask=mask,
                        method="combined",
                        txt_op="memory",
                        txt_file=None,
                        base_name=base_name,
                        is_train=is_train,
                        annotation=annotation
                    )
                    self._processed_files += 1
                    
                    del image, mask, annotation
                    gc.collect()

            batch = []
            for i, triplet in enumerate(train_gen):
                if number_of_images and i >= number_of_images // 2:
                    break
                batch.append(triplet)
                if len(batch) >= BATCH_SIZE:
                    process_batch(batch, is_train=True)
                    batch = []
            if batch:
                process_batch(batch, is_train=True)

            batch = []
            for i, triplet in enumerate(val_gen):
                if number_of_images and i >= number_of_images // 2:
                    break
                batch.append(triplet)
                if len(batch) >= BATCH_SIZE:
                    process_batch(batch, is_train=False)
                    batch = []
            if batch:
                process_batch(batch, is_train=False)

            logger.info(f"Augmentation completed. Processed {self._processed_files} files.")
            return {"status": "success"}

        except Exception as e:
            logger.error(f"Augmentation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
            
    async def stop_augmentation(self):
        self._progress = 0
        self._processed_files = 0
        self._total_files = 0
        self.stop = True
        return {"status": "stopped", "message": "Augmentation stopped"}

    def clear_output_directories(self):
        for path in [
            self.aug_train_img_path, self.aug_train_mask_path, self.aug_train_annotation_path,
            self.aug_val_img_path, self.aug_val_mask_path, self.aug_val_annotation_path
        ]:
            if os.path.exists(path):
                for file in os.listdir(path):
                    file_path = os.path.join(path, file)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        logger.error(f"Failed to delete {file_path}: {e}")
                        continue
            else:
                os.makedirs(path, exist_ok=True)