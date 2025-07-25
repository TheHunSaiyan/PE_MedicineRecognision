import os
import glob
import cv2
import numpy as np
import random
import shutil
import qrcode

from PIL import Image
from typing import Dict, Any, Optional

from config import AppConfig
from logger import logger

class AugmentImage:
    def __init__(self, stop_event=None):
        self.image_path = AppConfig.SPLIT_TRAIN_IMAGES
        self.mask_path = AppConfig.SPLIT_TRAIN_MASKS
        self.annotation_path = AppConfig.SPLIT_TRAIN_LABELS
        self.aug_img_path = AppConfig.AUG_IMAGES
        self.aug_mask_path = AppConfig.AUG_MASKS
        self.aug_annotation_path = AppConfig.AUG_ANN
        self.backgrounds_path = AppConfig.BACKGROUND_IMAGES
        self.stop_event = stop_event
        self._current_progress = 0
        self._total_files = 0
        self._processed_files = 0


    def clear_output_directories(self):
        for path in [self.aug_img_path, self.aug_mask_path, self.aug_annotation_path]:
            if os.path.exists(path):
                for file in os.listdir(path):
                    file_path = os.path.join(path, file)
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Failed to delete {file_path}: {e}")
            else:
                os.makedirs(path, exist_ok=True)

    def save_data(self, image, mask, method, txt_op="copy", txt_file=None, base_name=None):
        if image is None or image.size == 0:
           print("Warning: Empty image, skipping save.")
           return
        if mask is None or mask.size == 0:
           print("Warning: Empty mask, skipping save.")
           return
       
        os.makedirs(self.aug_img_path, exist_ok=True)
        os.makedirs(self.aug_mask_path, exist_ok=True)
        os.makedirs(self.aug_annotation_path, exist_ok=True)
    
        img_out_path = os.path.join(self.aug_img_path, f"{base_name}.png")
        mask_out_path = os.path.join(self.aug_mask_path, f"{base_name}.png")
        ann_out_path = os.path.join(self.aug_annotation_path, f"{base_name}.txt")
    
        cv2.imwrite(img_out_path, image)
        cv2.imwrite(mask_out_path, mask)
    
        if txt_op == "copy" and txt_file and os.path.exists(txt_file):
            shutil.copy(txt_file, ann_out_path)


    def get_image_triplets(self):
        files = sorted(glob.glob(os.path.join(self.image_path, "*.*")))
        self._total_files = 0
        
        print(f"Found {len(files)} image files")
        
        valid_triplets = []
        for img_file in files:
            base_name = os.path.splitext(os.path.basename(img_file))[0]
            mask_file = os.path.join(self.mask_path, f"{base_name}.jpg")
            ann_file = os.path.join(self.annotation_path, f"{base_name}.txt")
            if os.path.exists(mask_file) and os.path.exists(ann_file):
                valid_triplets.append((img_file, mask_file, ann_file))
        
        self._total_files = len(valid_triplets)
        for triplet in valid_triplets:
            yield triplet


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
    
    def apply_zoom(self, image, mask):
        h, w = image.shape[:2]
        scale = random.uniform(1.1, 1.4)
        new_h, new_w = int(h * scale), int(w * scale)
        resized_img = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        resized_mask = cv2.resize(mask, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
        top = (new_h - h) // 2
        left = (new_w - w) // 2
        return resized_img[top:top + h, left:left + w], resized_mask[top:top + h, left:left + w]
    
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
        
        return {
            "current": self._processed_files,
            "total": self._total_files,
            "progress": progress,
            "status": "Processing" if progress < 100 else "Completed"
        }

    def start_augmentation(self, data):
        self.clear_output_directories()
        self._processed_files = 0
        self._total_files = 0
        
        for img_file, mask_file, ann_file in self.get_image_triplets():
            base_name = os.path.splitext(os.path.basename(img_file))[0]
            image = cv2.imread(img_file)
            mask = cv2.imread(mask_file)
    
            if image is None or mask is None:
                continue
    
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
            if data.get("zoom"):
                image, mask = self.apply_zoom(image, mask)
            if data.get("change_background"):
                image = self.apply_background_change(image, mask)
            if data.get("qr_code"):
               image = self.qr_code(image)
    
            self.save_data(image, mask, method="combined", txt_op="copy", txt_file=ann_file, base_name=base_name)
            self._processed_files += 1
            
        logger.info("Successfull augmentation.")
        return {
            "status": "success"
        }

