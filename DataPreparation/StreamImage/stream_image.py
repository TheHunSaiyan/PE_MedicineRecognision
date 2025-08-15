import cv2
import random
import concurrent.futures
import numpy as np
import os
import shutil
import re
import redis
import pickle

from fastapi import HTTPException, status
from skimage.feature import local_binary_pattern
from tqdm import tqdm
from typing import Dict, List, Tuple

from Config.config import AppConfig
from Logger.logger import logger

class StreamImage():
    def __init__(self):
        self.progress = 0
        self.processed = 0
        self.total = 0
        self.is_processing = False
        self.selected_mode = ""
        
        self.redis = redis.Redis(
            host="redis",
            port=AppConfig.REDIS_PORT,
            db=3,
            decode_responses=False
        )
        self.cache_prefix = "stream_img:"
        
    def serialize_image(self, image: np.ndarray) -> bytes:
        return pickle.dumps(image)
    
    def deserialize_image(self, image_bytes: bytes) -> np.ndarray:
        return pickle.loads(image_bytes)
    
    def get_cache_key(self, operation: str, filename: str) -> str:
        return f"{self.cache_prefix}{operation}:{filename}"
    
    def extract_pill_name(self, filename: str) -> str:
        match = re.match(r'^(.+?)_[su]_', filename)
        if match:
            return match.group(1)
        return "unknown_pill"
    
    def ensure_pill_directory(self, base_path: str, filename: str) -> str:
        pill_name = self.extract_pill_name(filename)
        pill_dir = os.path.join(base_path, pill_name)
        os.makedirs(pill_dir, exist_ok=True)
        return pill_dir
    
    async def get_data_availability(self):
        return {
            "images": os.path.exists(AppConfig.ORIGINAL_IMAGES) and bool(os.listdir(AppConfig.ORIGINAL_IMAGES)),
            "mask_images": os.path.exists(AppConfig.ORIGINAL_MASKS) and bool(os.listdir(AppConfig.ORIGINAL_MASKS)),
            "split": (
                    os.path.exists(AppConfig.CONSUMER_IMAGES) and 
                    os.path.exists(AppConfig.REFERENCE_IMAGES) and
                    bool(os.listdir(AppConfig.CONSUMER_IMAGES)) and 
                    bool(os.listdir(AppConfig.REFERENCE_IMAGES))
                ),
            "background_changed": (
                                os.path.exists(AppConfig.CONSUMER_IMAGES_WO_BG) and 
                                os.path.exists(AppConfig.REFERENCE_IMAGES_WO_BG) and
                                bool(os.listdir(AppConfig.CONSUMER_IMAGES_WO_BG)) and 
                                bool(os.listdir(AppConfig.REFERENCE_IMAGES_WO_BG))
                            )
        }
        
    async def split_consumer_reference(self):
        try:
            logger.info("Spliting images into consumer and reference...")
            os.makedirs(AppConfig.CONSUMER_IMAGES, exist_ok=True)
            os.makedirs(AppConfig.REFERENCE_IMAGES, exist_ok=True)
            os.makedirs(AppConfig.CONSUMER_MASK_IMAGES, exist_ok=True)
            os.makedirs(AppConfig.REFERENCE_MASK_IMAGES, exist_ok=True)
            
            image_files = [f for f in os.listdir(AppConfig.ORIGINAL_IMAGES) if f.endswith('.jpg')]
            mask_files = [f for f in os.listdir(AppConfig.ORIGINAL_MASKS) if f.endswith('.jpg')]
            
            s_pairs = []
            u_pairs = []
            
            for img_file in image_files:
                base_name = os.path.splitext(img_file)[0]
                if '_s_' in base_name:
                    mask_file = base_name + '.jpg'
                    if mask_file in mask_files:
                        s_pairs.append((img_file, mask_file))
                elif '_u_' in base_name:
                    mask_file = base_name + '.jpg'
                    if mask_file in mask_files:
                        u_pairs.append((img_file, mask_file))
                else:
                    logger.warning(f"Skipping {base_name} because of invalid name.")
                    
            if len(s_pairs) < 1 or len(u_pairs) < 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Not enough image pairs with 's' and 'u' tags found"
                )
                
            selected_s = random.choice(s_pairs)
            selected_u = random.choice(u_pairs)
            
            reference_pairs = [selected_s, selected_u]
            
            consumer_pairs = []

            for pair in s_pairs:
                if pair != selected_s:
                    consumer_pairs.append(pair)
            for pair in u_pairs:
                if pair != selected_u:
                    consumer_pairs.append(pair)
                    
            for img_file, mask_file in reference_pairs:
                ref_img_pill_dir = self.ensure_pill_directory(AppConfig.REFERENCE_IMAGES, img_file)
                ref_mask_pill_dir = self.ensure_pill_directory(AppConfig.REFERENCE_MASK_IMAGES, mask_file)
                
                shutil.copy2(
                    os.path.join(AppConfig.ORIGINAL_IMAGES, img_file),
                    os.path.join(ref_img_pill_dir, img_file))
                shutil.copy2(
                    os.path.join(AppConfig.ORIGINAL_MASKS, mask_file),
                    os.path.join(ref_mask_pill_dir, mask_file))

            for img_file, mask_file in consumer_pairs:
                cons_img_pill_dir = self.ensure_pill_directory(AppConfig.CONSUMER_IMAGES, img_file)
                cons_mask_pill_dir = self.ensure_pill_directory(AppConfig.CONSUMER_MASK_IMAGES, mask_file)
                
                shutil.copy2(
                    os.path.join(AppConfig.ORIGINAL_IMAGES, img_file),
                    os.path.join(cons_img_pill_dir, img_file))
                shutil.copy2(
                    os.path.join(AppConfig.ORIGINAL_MASKS, mask_file),
                    os.path.join(cons_mask_pill_dir, mask_file))
                
            return {
                "status": "success"
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error during splitting images: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error during splitting images: {str(e)}"
            )
    
    async def change_background(self):
        try:
            logger.info("Changing image backgrounds with Redis caching...")
             
            os.makedirs(AppConfig.CONSUMER_IMAGES_WO_BG, exist_ok=True)
            os.makedirs(AppConfig.REFERENCE_IMAGES_WO_BG, exist_ok=True)
            
            for mode in ["consumer", "reference"]:
                paths = self.path_selector(mode)
                image_files = [f for f in os.listdir(paths["images"]) if f.endswith('.jpg')]
                
                bg_color = (145, 145, 151)
                
                for img_file in image_files:
                    cache_key = self.get_cache_key("bg_change", img_file)
                    pill_name = self.extract_pill_name(img_file)
                    output_dir = AppConfig.CONSUMER_IMAGES_WO_BG if mode == "consumer" else AppConfig.REFERENCE_IMAGES_WO_BG
                    output_path = os.path.join(self.ensure_pill_directory(output_dir, img_file), img_file)
                    
                    cached_img = self.redis.get(cache_key)
                    if cached_img:
                        with open(output_path, 'wb') as f:
                            f.write(cached_img)
                        continue
                    
                    mask_file = img_file
                    img_path = os.path.join(paths["images"], pill_name, img_file)
                    mask_path = os.path.join(paths["masks"], pill_name, mask_file)
                    
                    image = cv2.imread(img_path)
                    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
                    
                    mask = cv2.resize(mask, (image.shape[1], image.shape[0]))
                    mask = cv2.threshold(mask, 128, 255, cv2.THRESH_BINARY)[1].astype(np.uint8)
                    
                    background = np.ones(image.shape, dtype=np.uint8)
                    background[:, :] = bg_color
                    
                    foreground = cv2.bitwise_and(image, image, mask=mask)
                    background = cv2.bitwise_and(background, background, mask=cv2.bitwise_not(mask))
                    output_image = cv2.add(foreground, background)
                    
                    cv2.imwrite(output_path, output_image)
                    self.redis.set(cache_key, self.serialize_image(output_image), ex=86400)
            
            return {"status": "success"}
        
        except Exception as e:
            logger.error(f"Error during background change: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error during background change: {str(e)}"
            )
        
    def path_selector(self, mode: str) -> dict:
        if mode.lower() == "consumer":
            return {
                "images": AppConfig.CONSUMER_IMAGES,
                "masks": AppConfig.CONSUMER_MASK_IMAGES,
                "wo_bg": AppConfig.CONSUMER_IMAGES_WO_BG,
                "contour": AppConfig.CONSUMER_CONTOUR,
                "lbp": AppConfig.CONSUMER_LBP,
                "rgb": AppConfig.CONSUMER_RGB,
                "texture": AppConfig.CONSUMER_TEXTURE
            }
        elif mode.lower() == "reference":
            return {
                "images": AppConfig.REFERENCE_IMAGES,
                "masks": AppConfig.REFERENCE_MASK_IMAGES,
                "wo_bg": AppConfig.REFERENCE_IMAGES_WO_BG,
                "contour": AppConfig.REFERENCE_CONTOUR,
                "lbp": AppConfig.REFERENCE_LBP,
                "rgb": AppConfig.REFERENCE_RGB,
                "texture": AppConfig.REFERENCE_TEXTURE
            }
        else:
            self.is_processing = False
            logger.error("Invalid operation mode.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Invalid operation mode."
            )
        
    def load_files(self, dir1: str, dir2: str, ext1: str, ext2: str) -> Tuple[List[str], List[str]]:
        files1 = []
        files2 = []
        
        for root, _, filenames in os.walk(dir1):
            for f in filenames:
                if f.endswith(ext1):
                    files1.append(os.path.join(root, f))
        
        for root, _, filenames in os.walk(dir2):
            for f in filenames:
                if f.endswith(ext2):
                    files2.append(os.path.join(root, f))
        
        files1 = sorted(files1)
        files2 = sorted(files2)
        
        if len(files1) != len(files2):
            self.is_processing = False
            logger.error("Number of images and masks don't match.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Number of images and masks don't match."
            )
        return files1, files2
    
    def draw_bounding_box(self, in_img: np.ndarray, seg_map: np.ndarray, output_path: str) -> None:
        n_objects, _, stats, _ = cv2.connectedComponentsWithStats(
            seg_map, connectivity=8, ltype=cv2.CV_32S
        )

        max_area = 0
        max_x, max_y, max_w, max_h = None, None, None, None

        for i in range(1, n_objects):
            x, y, w, h, area = stats[i]
            if area > 100 and area > max_area:
                max_x, max_y, max_w, max_h = x, y, w, h
                max_area = area

        if max_area > 0:
            center_x = max_x + max_w / 2
            center_y = max_y + max_h / 2
            side_length = max(max_w, max_h)

            square_x = max(0, int(center_x - side_length / 2))
            square_y = max(0, int(center_y - side_length / 2))
            square_x_end = min(in_img.shape[1], square_x + side_length)
            square_y_end = min(in_img.shape[0], square_y + side_length)

            obj = in_img[square_y:square_y_end, square_x:square_x_end]

            if obj.size != 0:
                cv2.imwrite(output_path, obj)
                
    def process_image(self, image_paths: Tuple[str, str], rgb_path: str) -> None:
        color_path, mask_path = image_paths
        output_name = os.path.basename(color_path)
        cache_key = self.get_cache_key("rgb", output_name)
        
        cached_img = self.redis.get(cache_key)
        if cached_img:
            output_pill_dir = self.ensure_pill_directory(rgb_path, output_name)
            with open(os.path.join(output_pill_dir, output_name), 'wb') as f:
                f.write(cached_img)
            self.processed += 1
            self.progress = int((self.processed / self.total) * 100)
            return
        
        output_pill_dir = self.ensure_pill_directory(rgb_path, output_name)
        output_file = os.path.join(output_pill_dir, output_name)
        color_img = cv2.imread(str(color_path), 1)
        mask_img = cv2.imread(str(mask_path), 0)
        
        self.draw_bounding_box(color_img, mask_img, output_file)
        
        with open(output_file, 'rb') as f:
            self.redis.set(cache_key, f.read(), ex=86400)
        
        self.processed += 1
        self.progress = int((self.processed / self.total) * 100)
        
    def save_rgb_images(self, bg_changed_path: str, masks_path: str, rgb_path: str) -> None:
        color_images, mask_images = self.load_files(
            bg_changed_path, masks_path, ".jpg", ".jpg"
        )
        self.total = len(color_images)
        self.processed = 0
        self.progress = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            list(tqdm(
                executor.map(self.process_image, 
                           zip(color_images, mask_images),
                           [rgb_path]*len(color_images)),
                total=len(color_images),
                desc="RGB images"
            ))
            
    def create_contour_images(self, args) -> None:
        try:
            cropped_image, output_path = args
            output_name = os.path.basename(output_path)
            cache_key = self.get_cache_key("contour", output_name)
            
            cached_img = self.redis.get(cache_key)
            if cached_img:
                with open(output_path, 'wb') as f:
                    f.write(cached_img)
                self.processed += 1
                self.progress = int((self.processed / self.total) * 100)
                return
                
            if cropped_image is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to read input image."
                )
                
            blurred_img = cv2.GaussianBlur(cropped_image, (7, 7), 0)
            edges = cv2.Canny(blurred_img, 10, 30)
            success = cv2.imwrite(output_path, edges)
            
            if success:
                with open(output_path, 'rb') as f:
                    self.redis.set(cache_key, f.read(), ex=86400)
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to write image to {output_path}"
                )
                
            self.processed += 1
            self.progress = int((self.processed / self.total) * 100)
        except Exception as e:
            logger.error(f"Error processing contour image: {str(e)}")
            raise
        
    def save_contour_images(self, rgb_path: str, contour_path: str) -> None:
        args_list = []
        for root, _, filenames in os.walk(rgb_path):
            for img_file in filenames:
                if img_file.endswith(".jpg"):
                    img_path = os.path.join(root, img_file)
                    pill_name = self.extract_pill_name(img_file)
                    contour_pill_dir = os.path.join(contour_path, pill_name)
                    os.makedirs(contour_pill_dir, exist_ok=True)
                    output_path = os.path.join(contour_pill_dir, img_file)
                    
                    args_list.append((cv2.imread(img_path, 0), output_path))
        
        self.total = len(args_list)
        self.processed = 0
        self.progress = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(self.create_contour_images, args) for args in args_list]
            concurrent.futures.wait(futures)
            
    def create_texture_images(self, args) -> None:
        cropped_image, output_path = args
        output_name = os.path.basename(output_path)
        cache_key = self.get_cache_key("texture", output_name)
        
        if self.redis.exists(cache_key):
            with open(output_path, 'wb') as f:
                f.write(self.redis.get(cache_key))
            self.processed += 1
            self.progress = int((self.processed / self.total) * 100)
            return
            
        blurred_img = cv2.GaussianBlur(cropped_image, (7, 7), 0)
        blurred_img = cv2.GaussianBlur(blurred_img, (15, 15), 0)
        sub_img = cv2.subtract(cropped_image, blurred_img)
        result = sub_img * 15
        
        cv2.imwrite(output_path, result)
        with open(output_path, 'rb') as f:
            self.redis.set(cache_key, f.read(), ex=86400)
            
        self.processed += 1
        self.progress = int((self.processed / self.total) * 100)
        
    def save_texture_images(self, rgb_path: str, texture_path: str) -> None:
        args_list = []
        for root, _, filenames in os.walk(rgb_path):
            for img_file in filenames:
                if img_file.endswith(".jpg"):
                    img_path = os.path.join(root, img_file)
                    pill_name = self.extract_pill_name(img_file)
                    texture_pill_dir = os.path.join(texture_path, pill_name)
                    os.makedirs(texture_pill_dir, exist_ok=True)
                    output_path = os.path.join(texture_pill_dir, img_file)
                    
                    args_list.append((cv2.imread(img_path, 0), output_path))
        
        self.total = len(args_list)
        self.processed = 0
        self.progress = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(self.create_texture_images, args) for args in args_list]
            concurrent.futures.wait(futures)
            
    def process_lbp_image(self, args) -> None:
        img_gray, dst_image_path = args
        output_name = os.path.basename(dst_image_path)
        cache_key = self.get_cache_key("lbp", output_name)
        
        if self.redis.exists(cache_key):
            with open(dst_image_path, 'wb') as f:
                f.write(self.redis.get(cache_key))
            self.processed += 1
            self.progress = int((self.processed / self.total) * 100)
            return
            
        lbp_image = local_binary_pattern(image=img_gray, P=8, R=2, method="default")
        lbp_image = np.clip(lbp_image, 0, 255)
        
        cv2.imwrite(dst_image_path, lbp_image)
        with open(dst_image_path, 'rb') as f:
            self.redis.set(cache_key, f.read(), ex=86400)
            
        self.processed += 1
        self.progress = int((self.processed / self.total) * 100)
        
    def save_lbp_images(self, rgb_path: str, lbp_path: str) -> None:
        args_list = []
        for root, _, filenames in os.walk(rgb_path):
            for img_file in filenames:
                if img_file.endswith(".jpg"):
                    img_path = os.path.join(root, img_file)
                    pill_name = self.extract_pill_name(img_file)
                    lbp_pill_dir = os.path.join(lbp_path, pill_name)
                    os.makedirs(lbp_pill_dir, exist_ok=True)
                    output_path = os.path.join(lbp_pill_dir, f"lbp_{img_file}")
                    
                    args_list.append((cv2.imread(img_path, 0), output_path))
        
        self.total = len(args_list)
        self.processed = 0
        self.progress = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(self.process_lbp_image, args) for args in args_list]
            concurrent.futures.wait(futures)
            
    def clear_cache(self, mode: str = None):
        try:
            if mode:
                keys = self.redis.keys(f"{self.cache_prefix}{mode}:*")
            else:
                keys = self.redis.keys(f"{self.cache_prefix}*")
                
            if keys:
                self.redis.delete(*keys)
            logger.info(f"Cleared Redis cache for {mode if mode else 'all operations'}")
        except Exception as e:
            logger.error(f"Error clearing Redis cache: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error clearing Redis cache: {str(e)}"
            )
        
    def start_stream_images(self, data: Dict[str, any]):
        logger.info("Creating Stream Images")
        
        if self.is_processing:
            return {"status": "error", "message": "Processing already in progress"}
        
        self.selected_mode = data.get("mode", "").lower()
        if self.selected_mode not in ["consumer", "reference"]:
            return {"status": "error", "message": "Invalid mode selected"}
        
        try:
            self.is_processing = True
            self.progress = 0
            self.processed = 0
            self.total = 0
            
            paths = self.path_selector(self.selected_mode)
        
            os.makedirs(paths["rgb"], exist_ok=True)
            os.makedirs(paths["contour"], exist_ok=True)
            os.makedirs(paths["texture"], exist_ok=True)
            os.makedirs(paths["lbp"], exist_ok=True)
            
            self.clear_output()
            
            self.save_rgb_images(paths["wo_bg"], paths["masks"], paths["rgb"])
            self.save_contour_images(paths["rgb"], paths["contour"])
            self.save_texture_images(paths["rgb"], paths["texture"])
            self.save_lbp_images(paths["rgb"], paths["lbp"])
                
            return {
                "status": "success", 
                "message": f"{self.selected_mode.capitalize()} stream images created successfully"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.is_processing = False
            logger.error(f"Error during stream image creation: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error during stream image creation: {str(e)}"
            )
        finally:
            self.is_processing = False
    
    async def get_progress(self):
        logger.info({
            "progress": self.progress,
            "processed": self.processed,
            "total": self.total,
            "is_processing": self.is_processing
        })
        return {
            "progress": self.progress,
            "processed": self.processed,
            "total": self.total,
            "is_processing": self.is_processing
        }
        
    def clear_output(self):
        try:
            paths = self.path_selector(self.selected_mode)
            
            self.clear_cache(self.selected_mode)
            
            for output_type in ["rgb", "contour", "texture", "lbp"]:
                if os.path.exists(paths[output_type]):
                    for root, dirs, files in os.walk(paths[output_type]):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                if os.path.isfile(file_path):
                                    os.unlink(file_path)
                            except Exception as e:
                                logger.error(f"Failed to delete {file_path}: {str(e)}")
                        
            logger.info(f"Cleared output directories and cache for {self.selected_mode} mode")
            
        except Exception as e:
            logger.error(f"Error clearing output: {str(e)}")
            raise