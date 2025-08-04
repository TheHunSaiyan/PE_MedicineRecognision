import cv2
import random
import concurrent.futures
import numpy as np
import os
import shutil

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
                shutil.copy2(
                    os.path.join(AppConfig.ORIGINAL_IMAGES, img_file),
                    os.path.join(AppConfig.REFERENCE_IMAGES, img_file))
                shutil.copy2(
                    os.path.join(AppConfig.ORIGINAL_MASKS, mask_file),
                    os.path.join(AppConfig.REFERENCE_MASK_IMAGES, mask_file))

            for img_file, mask_file in consumer_pairs:
                shutil.copy2(
                    os.path.join(AppConfig.ORIGINAL_IMAGES, img_file),
                    os.path.join(AppConfig.CONSUMER_IMAGES, img_file))
                shutil.copy2(
                    os.path.join(AppConfig.ORIGINAL_MASKS, mask_file),
                    os.path.join(AppConfig.CONSUMER_MASK_IMAGES, mask_file))
                
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
            logger.info("Changing image backgrounds...")
             
            os.makedirs(AppConfig.CONSUMER_IMAGES_WO_BG, exist_ok=True)
            os.makedirs(AppConfig.REFERENCE_IMAGES_WO_BG, exist_ok=True)
            
            for mode in ["consumer", "reference"]:
                paths = self.path_selector(mode)
                image_files = [f for f in os.listdir(paths["images"]) if f.endswith('.jpg')]
                mask_files = [f for f in os.listdir(paths["masks"]) if f.endswith('.jpg')]
                
                image_mask_pairs = []
                for img_file in image_files:
                    mask_file = img_file
                    if mask_file in mask_files:
                        image_mask_pairs.append((img_file, mask_file))
                        
                bg_color = (145, 145, 151)
                
                for img_file, mask_file in image_mask_pairs:
                    img_path = os.path.join(paths["images"], img_file)
                    mask_path = os.path.join(paths["masks"], mask_file)
                    
                    image = cv2.imread(img_path)
                    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
                    
                    mask = cv2.resize(mask, (image.shape[1], image.shape[0]))
                    mask = cv2.threshold(mask, 128, 255, cv2.THRESH_BINARY)[1].astype(np.uint8)
                    
                    background = np.ones(image.shape, dtype=np.uint8)
                    background[:, :, 0] = bg_color[0]
                    background[:, :, 1] = bg_color[1]
                    background[:, :, 2] = bg_color[2]
                    
                    foreground = cv2.bitwise_and(image, image, mask=mask)
                    
                    background = cv2.bitwise_and(background, background, mask=cv2.bitwise_not(mask))
                    
                    output_image = cv2.add(foreground, background)
                    
                    output_dir = AppConfig.CONSUMER_IMAGES_WO_BG if mode == "consumer" else AppConfig.REFERENCE_IMAGES_WO_BG
                    output_path = os.path.join(output_dir, img_file)
                    cv2.imwrite(output_path, output_image)
            
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
        files1 = sorted([os.path.join(dir1, f) for f in os.listdir(dir1) if f.endswith(ext1)])
        files2 = sorted([os.path.join(dir2, f) for f in os.listdir(dir2) if f.endswith(ext2)])
        
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
        output_file = os.path.join(rgb_path, output_name)
        color_img = cv2.imread(str(color_path), 1)
        mask_img = cv2.imread(str(mask_path), 0)
        self.draw_bounding_box(color_img, mask_img, output_file)
        
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
            if cropped_image is None:
                self.is_processing = False
                logger.error("Failed to read input image.")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to read input image."
                )
                
            blurred_img = cv2.GaussianBlur(cropped_image, (7, 7), 0)
            edges = cv2.Canny(blurred_img, 10, 30)
            success = cv2.imwrite(output_path, edges)
            
            if not success:
                logger.error("Failed to write image to {output_path}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to write image to {output_path}"
                )
                
            self.processed += 1
            self.progress = int((self.processed / self.total) * 100)
        except Exception as e:
            logger.error("Error processing contour image: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing contour image: {str(e)}"
            )
        
    def save_contour_images(self, rgb_path: str, contour_path: str) -> None:
        rgb_images = [os.path.join(rgb_path, f) 
                     for f in os.listdir(rgb_path) if f.endswith(".jpg")]
        args_list = [(cv2.imread(img_path, 0), 
             os.path.join(contour_path, os.path.basename(img_path)))
            for img_path in rgb_images]
        
        self.total = len(args_list)
        self.processed = 0
        self.progress = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(self.create_contour_images, args) for args in args_list]
            concurrent.futures.wait(futures)
            
    def create_texture_images(self, args) -> None:
        cropped_image, output_path = args
        blurred_img = cv2.GaussianBlur(cropped_image, (7, 7), 0)
        blurred_img = cv2.GaussianBlur(blurred_img, (15, 15), 0)
        sub_img = cv2.subtract(cropped_image, blurred_img)
        cv2.imwrite(output_path, sub_img * 15)
        
        self.processed += 1
        self.progress = int((self.processed / self.total) * 100)
        
    def save_texture_images(self, rgb_path: str, texture_path: str) -> None:
        rgb_images = [os.path.join(rgb_path, f) 
                     for f in os.listdir(rgb_path) if f.endswith(".jpg")]
        args_list = [(cv2.imread(img_path, 0), 
             os.path.join(texture_path, os.path.basename(img_path)))
            for img_path in rgb_images]
        
        self.total = len(args_list)
        self.processed = 0
        self.progress = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(self.create_texture_images, args) for args in args_list]
            concurrent.futures.wait(futures)
            
    def process_lbp_image(self, args) -> None:
        img_gray, dst_image_path = args
        lbp_image = local_binary_pattern(image=img_gray, P=8, R=2, method="default")
        lbp_image = np.clip(lbp_image, 0, 255)
        cv2.imwrite(dst_image_path, lbp_image)
        
        self.processed += 1
        self.progress = int((self.processed / self.total) * 100)
        
    def save_lbp_images(self, rgb_path: str, lbp_path: str) -> None:
        rgb_images = [os.path.join(rgb_path, f) 
                     for f in os.listdir(rgb_path) if f.endswith(".jpg")]
        args_list = [(cv2.imread(img_path, 0), 
                     os.path.join(lbp_path, f"lbp_{os.path.basename(img_path)}"))
                    for img_path in rgb_images]
        
        self.total = len(args_list)
        self.processed = 0
        self.progress = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(self.process_lbp_image, args) for args in args_list]
            concurrent.futures.wait(futures)
        
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
            
            if os.path.exists(paths["rgb"]):
                for file in os.listdir(paths["rgb"]):
                    file_path = os.path.join(paths["rgb"], file)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                    except Exception as e:
                        logger.error(f"Failed to delete {file_path}: {str(e)}")
            
            if os.path.exists(paths["contour"]):
                for file in os.listdir(paths["contour"]):
                    file_path = os.path.join(paths["contour"], file)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                    except Exception as e:
                        logger.error(f"Failed to delete {file_path}: {str(e)}")
            
            if os.path.exists(paths["texture"]):
                for file in os.listdir(paths["texture"]):
                    file_path = os.path.join(paths["texture"], file)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                    except Exception as e:
                        logger.error(f"Failed to delete {file_path}: {str(e)}")
            
            if os.path.exists(paths["lbp"]):
                for file in os.listdir(paths["lbp"]):
                    file_path = os.path.join(paths["lbp"], file)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                    except Exception as e:
                        logger.error(f"Failed to delete {file_path}: {str(e)}")
                        
            logger.info(f"Cleared output directories for {self.selected_mode} mode")
            
        except Exception as e:
            logger.error(f"Error clearing output directories: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error clearing output directories: {str(e)}"
            )