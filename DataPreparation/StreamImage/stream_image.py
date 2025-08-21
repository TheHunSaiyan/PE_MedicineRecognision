import cv2
import concurrent.futures
import numpy as np
import os
import random
import re
import redis
import pickle
import shutil

from fastapi import HTTPException, status
from skimage.feature import local_binary_pattern
from tqdm import tqdm
from typing import Dict, List, Tuple

from Config.config import AppConfig
from DataPreparation.CreateMask.createmask import CreateMask
from Logger.logger import logger


class StreamImage():
    def __init__(self):
        """
        Initializes the StreamImage class with default values for progress tracking and Redis connection.

        Args:
            None

        Returns:
            None
        """

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
        self.createmask = CreateMask()

    def serialize_image(self, image: np.ndarray) -> bytes:
        """
        Serializes a NumPy image array into bytes using pickle.

        Args:
            image (np.ndarray): The image array to serialize.

        Returns:
            bytes: The serialized image as a byte stream.
        """

        return pickle.dumps(image)

    def deserialize_image(self, image_bytes: bytes) -> np.ndarray:
        """
        Deserializes an image from a bytes object to a NumPy ndarray.

        Args:
            image_bytes (bytes): The serialized image data in bytes format.

        Returns:
            np.ndarray: The deserialized image as a NumPy array.
        """

        return pickle.loads(image_bytes)

    def get_cache_key(self, operation: str, filename: str) -> str:
        """
        Generates a cache key string for a given operation and filename.
        Args:
            operation (str): The operation to be performed (e.g., 'read', 'write').
            filename (str): The name of the file associated with the operation.
        Returns:
            str: A formatted cache key combining the cache prefix, operation, and filename.
        """

        return f"{self.cache_prefix}{operation}:{filename}"

    def extract_pill_name(self, filename: str) -> str:
        """
        Extracts the pill name from a given filename using a regular expression.

        Args:
            filename (str): The filename from which to extract the pill name.

        Returns:
            str: The extracted pill name, or "unknown_pill" if the pattern does not match.
        """

        match = re.match(r'^(.+?)_[su]_', filename)
        if match:
            return match.group(1)
        return "unknown_pill"

    def ensure_pill_directory(self, base_path: str, filename: str) -> str:
        """
        Ensures that a directory for the specified pill exists within the given base path.

        Args:
            base_path (str): The base directory where pill directories are stored.
            filename (str): The filename from which to extract the pill name.

        Returns:
            str: The full path to the pill's directory.
        """

        pill_name = self.extract_pill_name(filename)
        pill_dir = os.path.join(base_path, pill_name)
        os.makedirs(pill_dir, exist_ok=True)
        return pill_dir

    async def get_data_availability(self):
        """
        Asynchronously checks the availability of various image data directories and their contents.
        Generates masks if they don't exist or are invalid.

        Args:
            None

        Returns:
            Dict[str, bool]: A dictionary indicating the availability of each data type.
        """

        def is_valid_mask(mask_path):
            """Check if a mask file is valid (contains only 0 and 255 values)"""
            try:
                mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
                if mask is None:
                    return False
                return set(np.unique(mask)).issubset({0, 255})
            except Exception:
                return False

        images_available = os.path.exists(AppConfig.ORIGINAL_IMAGES) and bool(
            os.listdir(AppConfig.ORIGINAL_IMAGES))

        if not images_available:
            return {
                "images": False,
                "mask_images": False,
                "split": False,
                "background_changed": False
            }

        masks_available = False
        if os.path.exists(AppConfig.ORIGINAL_MASKS) and os.listdir(AppConfig.ORIGINAL_MASKS):
            valid_mask_count = 0
            for mask_file in os.listdir(AppConfig.ORIGINAL_MASKS):
                mask_path = os.path.join(AppConfig.ORIGINAL_MASKS, mask_file)
                if is_valid_mask(mask_path):
                    valid_mask_count += 1

            image_count = len([f for f in os.listdir(AppConfig.ORIGINAL_IMAGES)
                               if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))])
            masks_available = (valid_mask_count == image_count)

        if not masks_available:
            logger.info(
                "Masks missing or invalid, generating masks from labels...")
            await self.generate_masks_from_labels()
            masks_available = True

        split_available = (
            os.path.exists(AppConfig.CONSUMER_IMAGES) and
            os.path.exists(AppConfig.REFERENCE_IMAGES) and
            bool(os.listdir(AppConfig.CONSUMER_IMAGES)) and
            bool(os.listdir(AppConfig.REFERENCE_IMAGES))
        )

        background_changed_available = (
            os.path.exists(AppConfig.CONSUMER_IMAGES_WO_BG) and
            os.path.exists(AppConfig.REFERENCE_IMAGES_WO_BG) and
            bool(os.listdir(AppConfig.CONSUMER_IMAGES_WO_BG)) and
            bool(os.listdir(AppConfig.REFERENCE_IMAGES_WO_BG))
        )

        return {
            "images": images_available,
            "mask_images": masks_available,
            "split": split_available,
            "background_changed": background_changed_available
        }

    async def generate_masks_from_labels(self):
        """
        Generate masks from segmentation labels using CreateMask class.

        Returns:
            None
        """
        logger.info("Generating masks from labels...")

        os.makedirs(AppConfig.ORIGINAL_MASKS, exist_ok=True)

        image_files = [f for f in os.listdir(AppConfig.ORIGINAL_IMAGES)
                       if f.lower().endswith('.jpg')]

        for img_file in image_files:
            img_path = os.path.join(AppConfig.ORIGINAL_IMAGES, img_file)
            base_name = os.path.splitext(img_file)[0]

            label_file = f"{base_name}.txt"
            label_path = os.path.join(AppConfig.ORIGINAL_LABELS, label_file)

            if not os.path.exists(label_path):
                logger.warning(f"No label file found for {img_file}")
                continue

            try:
                mask = self.createmask.process_data(
                    img_path, label_path, scale_factor=4)

                if mask is None:
                    logger.error(f"Failed to create mask for {img_file}")
                    continue

                self.createmask.save_masks(
                    mask, img_path, AppConfig.ORIGINAL_MASKS)
                logger.info(f"Generated mask: {base_name}")

            except Exception as e:
                logger.error(f"Error processing {img_file}: {str(e)}")
                continue

    async def split_consumer_reference(self):
        """
        Splits original images and masks into consumer and reference sets based on filename tags.

        Args:
            None

        Returns:
            dict: A dictionary with a "status" key indicating success.
        """

        try:
            logger.info("Spliting images into consumer and reference...")
            os.makedirs(AppConfig.CONSUMER_IMAGES, exist_ok=True)
            os.makedirs(AppConfig.REFERENCE_IMAGES, exist_ok=True)
            os.makedirs(AppConfig.CONSUMER_MASK_IMAGES, exist_ok=True)
            os.makedirs(AppConfig.REFERENCE_MASK_IMAGES, exist_ok=True)

            image_files = [f for f in os.listdir(
                AppConfig.ORIGINAL_IMAGES) if f.endswith('.jpg')]
            mask_files = [f for f in os.listdir(
                AppConfig.ORIGINAL_MASKS) if f.endswith('.jpg')]

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
                    logger.warning(
                        f"Skipping {base_name} because of invalid name.")

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
                ref_img_pill_dir = self.ensure_pill_directory(
                    AppConfig.REFERENCE_IMAGES, img_file)
                ref_mask_pill_dir = self.ensure_pill_directory(
                    AppConfig.REFERENCE_MASK_IMAGES, mask_file)

                shutil.copy2(
                    os.path.join(AppConfig.ORIGINAL_IMAGES, img_file),
                    os.path.join(ref_img_pill_dir, img_file))
                shutil.copy2(
                    os.path.join(AppConfig.ORIGINAL_MASKS, mask_file),
                    os.path.join(ref_mask_pill_dir, mask_file))

            for img_file, mask_file in consumer_pairs:
                cons_img_pill_dir = self.ensure_pill_directory(
                    AppConfig.CONSUMER_IMAGES, img_file)
                cons_mask_pill_dir = self.ensure_pill_directory(
                    AppConfig.CONSUMER_MASK_IMAGES, mask_file)

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
        """
        Asynchronously changes the background of images in specified directories using mask files,
        applies a uniform background color, and caches the processed images in Redis.

        Args:
            None

        Returns:
            dict: {"status": "success"} if processing completes without errors.
        """

        try:
            logger.info("Changing image backgrounds with Redis caching...")

            os.makedirs(AppConfig.CONSUMER_IMAGES_WO_BG, exist_ok=True)
            os.makedirs(AppConfig.REFERENCE_IMAGES_WO_BG, exist_ok=True)

            for mode in ["consumer", "reference"]:
                paths = self.path_selector(mode)
                image_files = [f for f in os.listdir(
                    paths["images"]) if f.endswith('.jpg')]

                bg_color = (145, 145, 145)

                for img_file in image_files:
                    cache_key = self.get_cache_key("bg_change", img_file)
                    pill_name = self.extract_pill_name(img_file)
                    output_dir = AppConfig.CONSUMER_IMAGES_WO_BG if mode == "consumer" else AppConfig.REFERENCE_IMAGES_WO_BG
                    output_path = os.path.join(
                        self.ensure_pill_directory(output_dir, img_file), img_file)

                    cached_img = self.redis.get(cache_key)
                    if cached_img:
                        with open(output_path, 'wb') as f:
                            f.write(cached_img)
                        continue

                    mask_file = img_file
                    img_path = os.path.join(
                        paths["images"], pill_name, img_file)
                    mask_path = os.path.join(
                        paths["masks"], pill_name, mask_file)

                    image = cv2.imread(img_path)
                    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)

                    mask = cv2.resize(mask, (image.shape[1], image.shape[0]))
                    mask = cv2.threshold(mask, 128, 255, cv2.THRESH_BINARY)[
                        1].astype(np.uint8)

                    background = np.ones(image.shape, dtype=np.uint8)
                    background[:, :] = bg_color

                    foreground = cv2.bitwise_and(image, image, mask=mask)
                    background = cv2.bitwise_and(
                        background, background, mask=cv2.bitwise_not(mask))
                    output_image = cv2.add(foreground, background)

                    cv2.imwrite(output_path, output_image)
                    self.redis.set(cache_key, self.serialize_image(
                        output_image), ex=86400)

            return {"status": "success"}

        except Exception as e:
            logger.error(f"Error during background change: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error during background change: {str(e)}"
            )

    async def stop_stream_image(self) -> Dict[str, str]:
        """
        Stop the current stream image creation process and clean up output directories.

        Args:
            None

        Returns:
            Dict[str, str]: A dictionary indicating the status of the operation.
        """
        if not self.is_processing:
            return {"status": "error", "message": "No stream image process is currently running"}

        try:
            self.is_processing = False

            self.clear_output()

            self.progress = 0
            self.processed = 0
            self.total = 0

            logger.info(
                "Stream image process stopped by user request and output directories cleaned")
            return {"status": "success", "message": "Stream image process stopped successfully and output directories cleared"}
        except Exception as e:
            logger.error(f"Error stopping stream image process: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error stopping stream image process: {str(e)}"
            )

    def path_selector(self, mode: str) -> dict:
        """
        Selects and returns a dictionary of image-related paths based on the specified operation mode.

        Args:
            mode (str): The operation mode, either "consumer" or "reference". Determines which set of paths to return.

        Returns:
            dict: A dictionary containing paths for images, masks, images without background, contour, LBP, RGB, and texture.
        """

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
        """
        Loads and returns lists of file paths from two directories, filtered by specified file extensions.

        Args:
            dir1 (str): Path to the first directory containing image files.
            dir2 (str): Path to the second directory containing mask files.
            ext1 (str): File extension to filter files in the first directory (e.g., '.jpg').
            ext2 (str): File extension to filter files in the second directory (e.g., '.png').

        Returns:
            Tuple[List[str], List[str]]: Two sorted lists containing the full paths of the filtered files from each directory.
        """

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
        """
        Detects the largest connected component in the segmentation map, computes a square bounding box 
        centered on this component, crops the corresponding region from the input image, and saves it to the specified output path.

        Args:
            in_img (np.ndarray): The input image from which the object will be cropped.
            seg_map (np.ndarray): The segmentation map indicating object regions.
            output_path (str): The file path where the cropped image will be saved.

        Returns:
            None
        """

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

    def process_image(self, args: Tuple[Tuple[str, str], str, Tuple[int, int]]) -> None:
        """
        Processes an image by reading color and mask files, drawing bounding boxes, resizing, caching, and saving the result.

        Args:
            args (Tuple[Tuple[str, str], str, Tuple[int, int]]): 
                - A tuple containing:
                    - (color_path, mask_path): Paths to the color image and mask image files.
                    - rgb_path: Path to the RGB image directory.
                    - max_size: Desired output image size as (height, width).

        Returns:
            None
        """

        (color_path, mask_path), rgb_path, max_size = args
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

        saved_img = cv2.imread(output_file)
        if saved_img is not None and (saved_img.shape[0] != max_size[0] or saved_img.shape[1] != max_size[1]):
            height_diff = max_size[0] - saved_img.shape[0]
            width_diff = max_size[1] - saved_img.shape[1]

            top = height_diff // 2
            bottom = height_diff - top
            left = width_diff // 2
            right = width_diff - left

            bg_color = (145, 145, 145)

            resized_img = cv2.copyMakeBorder(
                saved_img,
                top, bottom, left, right,
                cv2.BORDER_CONSTANT,
                value=bg_color
            )

            cv2.imwrite(output_file, resized_img)

        with open(output_file, 'rb') as f:
            self.redis.set(cache_key, f.read(), ex=86400)

        self.processed += 1
        self.progress = int((self.processed / self.total) * 100)

    def save_rgb_images(self, bg_changed_path: str, masks_path: str, rgb_path: str) -> None:
        """
        Processes and saves RGB images with bounding boxes drawn from the given background-changed and mask image directories.

        Args:
            bg_changed_path (str): Path to the directory containing background-changed color images.
            masks_path (str): Path to the directory containing mask images.
            rgb_path (str): Path to the directory where processed RGB images will be saved.

        Returns:
            None
        """

        color_images, mask_images = self.load_files(
            bg_changed_path, masks_path, ".jpg", ".jpg"
        )
        self.total = len(color_images)
        self.processed = 0
        self.progress = 0

        max_height = 0
        max_width = 0

        for color_path, mask_path in zip(color_images, mask_images):
            color_img = cv2.imread(str(color_path), 1)
            mask_img = cv2.imread(str(mask_path), 0)

            temp_file = os.path.join("/tmp", os.path.basename(color_path))
            self.draw_bounding_box(color_img, mask_img, temp_file)

            cropped_img = cv2.imread(temp_file)
            if cropped_img is not None:
                h, w = cropped_img.shape[:2]
                max_height = max(max_height, h)
                max_width = max(max_width, w)

            if os.path.exists(temp_file):
                os.remove(temp_file)

        max_size = (max_height, max_width)

        args_list = [((color_path, mask_path), rgb_path, max_size)
                     for color_path, mask_path in zip(color_images, mask_images)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = []
            for args in args_list:
                futures.append(executor.submit(self.process_image, args))

            for _ in tqdm(concurrent.futures.as_completed(futures),
                          total=len(args_list), desc="RGB images"):
                pass

    def create_contour_images(self, args) -> None:
        """
        Processes a cropped image to generate its contour image using Canny edge detection,
        saves the result to the specified output path, and caches the image in Redis for future use.

        Args:
            args (tuple): A tuple containing:
                - cropped_image (np.ndarray): The input image to process.
                - output_path (str): The file path where the processed image will be saved.

        Returns:
            None
        """

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

            gray = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2GRAY)
            grad_x = cv2.Sobel(gray, cv2.CV_16S, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_16S, 0, 1, ksize=3)
            abs_grad_x = cv2.convertScaleAbs(grad_x)
            abs_grad_y = cv2.convertScaleAbs(grad_y)
            edges = cv2.addWeighted(abs_grad_x, 1.5, abs_grad_y, 2.5, 0)
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
        """
        Processes all JPEG images in the specified directory, extracts pill names from filenames,
        and saves contour images to corresponding subdirectories.

        Args:
            rgb_path (str): Path to the directory containing RGB images.
            contour_path (str): Path to the directory where contour images will be saved.

        Returns:
            None
        """

        args_list = []
        for root, _, filenames in os.walk(rgb_path):
            for img_file in filenames:
                if img_file.endswith(".jpg"):
                    img_path = os.path.join(root, img_file)
                    pill_name = self.extract_pill_name(img_file)
                    contour_pill_dir = os.path.join(contour_path, pill_name)
                    os.makedirs(contour_pill_dir, exist_ok=True)
                    output_path = os.path.join(contour_pill_dir, img_file)

                    args_list.append(
                        (cv2.imread(img_path, cv2.IMREAD_COLOR), output_path))

        self.total = len(args_list)
        self.processed = 0
        self.progress = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(
                self.create_contour_images, args) for args in args_list]
            concurrent.futures.wait(futures)

    def create_texture_images(self, args) -> None:
        """
        Generates a texture-enhanced image from a cropped input image, saves it to disk, and caches the result in Redis.

        Args:
            args (tuple): A tuple containing:
                - cropped_image (np.ndarray): The input cropped image as a NumPy array.
                - output_path (str): The file path where the processed image will be saved.

        Returns:
            None
        """

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
        """
        Processes RGB images from the specified directory, generates texture images, and saves them to the target directory.

        Args:
            rgb_path (str): Path to the directory containing RGB images.
            texture_path (str): Path to the directory where texture images will be saved.

        Returns:
            None
        """

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
            futures = [executor.submit(
                self.create_texture_images, args) for args in args_list]
            concurrent.futures.wait(futures)

    def process_lbp_image(self, args) -> None:
        """
        Processes a grayscale image using Local Binary Pattern (LBP) and saves the result.

        Args:
            args (tuple): A tuple containing:
                - img_gray (np.ndarray): Grayscale image to process.
                - dst_image_path (str): Path to save the processed LBP image.

        Returns:
            None
        """

        img_gray, dst_image_path = args
        output_name = os.path.basename(dst_image_path)
        cache_key = self.get_cache_key("lbp", output_name)

        if self.redis.exists(cache_key):
            with open(dst_image_path, 'wb') as f:
                f.write(self.redis.get(cache_key))
            self.processed += 1
            self.progress = int((self.processed / self.total) * 100)
            return

        lbp_image = local_binary_pattern(
            image=img_gray, P=8, R=2, method="default")
        lbp_image = np.clip(lbp_image, 0, 255)

        cv2.imwrite(dst_image_path, lbp_image)
        with open(dst_image_path, 'rb') as f:
            self.redis.set(cache_key, f.read(), ex=86400)

        self.processed += 1
        self.progress = int((self.processed / self.total) * 100)

    def save_lbp_images(self, rgb_path: str, lbp_path: str) -> None:
        """
        Processes all JPEG images in the specified directory, computes their Local Binary Pattern (LBP) representations,
        and saves the resulting images to a target directory organized by pill name.

        Args:
            rgb_path (str): Path to the directory containing the original RGB images.
            lbp_path (str): Path to the directory where the LBP images will be saved.

        Returns:
            None
        """

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
            futures = [executor.submit(self.process_lbp_image, args)
                       for args in args_list]
            concurrent.futures.wait(futures)

    def clear_cache(self, mode: str = None):
        """
        Clears cached entries from Redis based on the specified mode.

        Args:
            mode (str, optional): The cache mode to clear. If None, clears all cache entries.

        Returns:
            None
        """

        try:
            if mode:
                keys = self.redis.keys(f"{self.cache_prefix}{mode}:*")
            else:
                keys = self.redis.keys(f"{self.cache_prefix}*")

            if keys:
                self.redis.delete(*keys)
            logger.info(
                f"Cleared Redis cache for {mode if mode else 'all operations'}")
        except Exception as e:
            logger.error(f"Error clearing Redis cache: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error clearing Redis cache: {str(e)}"
            )

    def start_stream_images(self, data: Dict[str, any]):
        """
        Starts the process of creating stream images based on the selected mode.

        Args:
            data (Dict[str, any]): A dictionary containing configuration data.

        Returns:
            dict: A dictionary with the status and message of the operation.
        """

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
        """
        Asynchronously retrieves the current progress status of the image processing task.

        Args:
            None

        Returns:
            dict: A dictionary with progress information.
        """

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
        """
        Clears the output directories and cache for the currently selected mode.

        Args:
            None

        Returns:
            None
        """

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
                                logger.error(
                                    f"Failed to delete {file_path}: {str(e)}")

            logger.info(
                f"Cleared output directories and cache for {self.selected_mode} mode")

        except Exception as e:
            logger.error(f"Error clearing output: {str(e)}")
            raise
