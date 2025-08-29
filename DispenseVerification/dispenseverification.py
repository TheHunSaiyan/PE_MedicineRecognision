import cv2
import glob
import numpy as np
import os
from pathlib import Path
import random
import tempfile
from typing import Any, Dict, List, Optional

from fastapi import File, Form, HTTPException, UploadFile, status
from pathlib import Path
from ultralytics import YOLO

from Config.config import AppConfig
from Controllers.camera_controller import CameraController
from Controllers.led_controller import LEDController
from DataPreparation.CreateMask.createmask import CreateMask
from Logger.logger import logger
from Manager.verification_manager import VerificationManager
from Models.recipe import Recipe, Medication


class DispenseVerification:
    def __init__(self, camera: CameraController, led: LEDController):
        """
        Initialize the Dispense Verification system.
        Sets up the camera and LED controllers and prepares the verification
        manager for pill dispensing validation operations.

        Args:
            camera (CameraController): Controller instance for camera operations.
            led (LEDController): Controller instance for LED lighting control.

        Returns:
            None
        """
        self.camera = camera
        self.led = led
        self.verification_manager = VerificationManager(camera, led)
        self.initialized = False
        self.recipe: Recipe = None
        self.yolo_model = YOLO(str(Path(AppConfig.SEGMENTATION_WEIGHTS)))
        logger.info(self.yolo_model.names)

    async def initialization(self):
        """
        Initialize the verification system components.

        Args:
            None

        Returns:
            dict: Dictionary containing initialization status and message.
        """
        try:
            self.initialized = await self.verification_manager.initialize()
            if not self.initialized:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to initialize verification system"
                )
            return {"status": True, "message": "Verification system initialized"}
        except Exception as e:
            logger.error(f"Verification initialization failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Initialization error: {str(e)}"
            )

    async def check_environment(self, image: UploadFile = File(...)):
        """
        Analyze the dispensing environment for proper verification conditions.

        Args:
            holder_id (str): Identifier for the medication holder being verified.

        Returns:
            dict: Dictionary containing environment analysis results.
        """
        if not self.initialized:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification system not initialized"
            )

        result = await self.verification_manager.analyze_environment(image)
        if not result["status"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        return result

    async def selected_recipe(self, data: Recipe) -> Dict[str, Any]:
        """
        Store the selected medication recipe for dispensing verification.

        Args:
            data (MedicationsData): The medication recipe data containing
                dispensing bay information and pill counts.

        Returns:
            dict: Dictionary containing status and message indicating
                successful storage of the recipe.
        """
        try:
            validated_data = Recipe(**data)

            self.recipe = validated_data

            logger.info(f"Received medication recipe: {validated_data}")

            return {
                "status": True,
                "message": "Recipe stored successfully",
            }

        except Exception as e:
            logger.error(f"Error storing recipe: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid recipe data: {str(e)}"
            )

    async def find_pill_images(self, pill_name: str) -> List[str]:
        """
        Find all reference images for a given pill name in the VERIF_IMAGES directory.

        Args:
            pill_name (str): The name of the pill to find images for

        Returns:
            List[str]: List of image file paths relative to the Appconfig.VERIF_IMAGES.
        """
        try:
            clean_pill_name = pill_name.lower().replace(' ', '_').replace('-', '_')

            logger.info(f"Searching for images matching: {clean_pill_name}")

            exact_patterns = [
                f"{clean_pill_name}.jpg"
            ]

            partial_patterns = [
                f"*{clean_pill_name}*.jpg"
            ]

            found_images = []

            for pattern in exact_patterns:
                search_path = str(Path(AppConfig.VERIF_IMAGES) / pattern)
                images = glob.glob(search_path)
                if images:
                    logger.info(f"Exact match found for {pattern}: {images}")
                found_images.extend(images)

            for pattern in partial_patterns:
                search_path = str(Path(AppConfig.VERIF_IMAGES) / pattern)
                images = glob.glob(search_path)
                if images:
                    logger.info(f"Partial match found for {pattern}: {images}")
                found_images.extend(images)

            unique_images = list(set(found_images))

            relative_images = []
            for img_path in unique_images:
                try:
                    relative_path = Path(img_path).relative_to(
                        AppConfig.VERIF_IMAGES).as_posix()
                    relative_images.append(relative_path)
                except ValueError:
                    continue

            logger.info(
                f"Final images found for {pill_name}: {relative_images}")
            return relative_images

        except Exception as e:
            logger.error(f"Error finding images for {pill_name}: {str(e)}")
            return []

    async def get_recipe_reference_images(self, recipe_data: Dict[str, Any] = None) -> dict:
        """
        Get reference images for all pills in the current recipe or provided recipe data.

        Args:
            recipe_data (Dict[str, Any], optional): Recipe data to use instead of stored recipe

        Returns:
            dict: Dictionary containing only image URLs for all pills in the recipe
        """
        if recipe_data:
            try:
                validated_recipe = Recipe(**recipe_data)
                recipe_to_use = validated_recipe
            except Exception as e:
                logger.error(f"Error validating recipe data: {str(e)}")
                return {"error": f"Invalid recipe data: {str(e)}"}
        elif self.recipe:
            recipe_to_use = self.recipe
        else:
            return {"error": "No recipe selected and no recipe data provided"}

        result = {}
        for bay_name, medications in recipe_to_use.medications.items():
            result[bay_name] = []
            for medication in medications:
                image_paths = await self.find_pill_images(medication.pill_name)

                logger.info(
                    f"Searching for {medication.pill_name}: found {len(image_paths)} images")

                image_urls = [f"/verif_images/{path}" for path in image_paths]

                result[bay_name].append({
                    "pill_name": medication.pill_name,
                    "count": medication.count,
                    "images": image_urls
                })

        return result

    def get_random_background(self, background_root: Path, target_size):
        """
        Pick a random jpg background from nested dirs and resize to target_size.

        Args:
            background_root: The folder where the backgrounds are located,
            target_size: The size the output image is supposed to be

        Returns:
            A resized background
        """
        all_backgrounds = list(background_root.rglob("*.jpg"))
        if not all_backgrounds:
            raise FileNotFoundError(
                "No backgrounds found in BACKGROUND_IMAGES")

        bg_path = random.choice(all_backgrounds)
        bg = cv2.imread(str(bg_path))

        if bg is None:
            raise ValueError(f"Failed to read background {bg_path}")

        return cv2.resize(bg, (target_size[0], target_size[1])), bg_path

    async def verify_dispense(self, image: UploadFile = File(...)):
        """
        Verify that the dispensed medication matches the selected recipe.
        Runs YOLO segmentation, extracts pill crops, assigns pills to bays,
        and compares against the saved recipe.

        Args:
            image (UploadFile): Captured image of the pill dispenser.

        Returns:
            dict: Verification results with per-bay expected vs found pills.
        """
        if not self.recipe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No recipe selected for verification"
            )

        try:
            img_bytes = await image.read()
            np_arr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            img_h, img_w = frame.shape[:2]

            results = self.yolo_model(frame, verbose=False)

            detected_medications = {
                "dispensing_bay_1": [],
                "dispensing_bay_2": [],
                "dispensing_bay_3": [],
                "dispensing_bay_4": []
            }

            bay_boundaries = [
                (0, img_w * 0.35),
                (img_w * 0.35, img_w * 0.50),
                (img_w * 0.50, img_w * 0.65),
                (img_w * 0.65, img_w)
            ]
            bay_names = ["dispensing_bay_1", "dispensing_bay_2",
                         "dispensing_bay_3", "dispensing_bay_4"]

            for r in results:
                if r.masks is None or r.masks.xy is None:
                    continue

                for mask_xy, cls_id in zip(r.masks.xy, r.boxes.cls):
                    polygon = mask_xy.astype(np.int32)

                    mask = np.zeros((img_h, img_w), dtype=np.uint8)
                    cv2.fillPoly(mask, [polygon], 255)

                    x, y, w, h = cv2.boundingRect(polygon)

                    txt_content = f"{int(cls_id)} " + \
                        " ".join([f"{x} {y}" for (x, y) in polygon]) + "\n"

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp_txt:
                        tmp_txt.write(txt_content.encode("utf-8"))
                        txt_path = tmp_txt.name

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_img:
                        cv2.imwrite(tmp_img.name, frame)
                        img_path = tmp_img.name

                    CreateMask.save_masks(
                        mask, img_path, AppConfig.VERIF_MASKS)
                    if w == 0 or h == 0:
                        continue
                    x, y = max(0, x), max(0, y)
                    w, h = min(w, img_w - x), min(h, img_h - y)

                    center_x = x + w // 2
                    bay = next((bay_names[i] for i, (start, end) in enumerate(bay_boundaries)
                                if start <= center_x < end), bay_names[-1])

                    pill_name = self.yolo_model.names[int(cls_id)]

                    pill_rgba = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
                    mask_resized = mask
                    pill_rgba[:, :, 3] = mask_resized
                    pill_crop = pill_rgba[y:y+h, x:x+w]

                    if pill_crop.size == 0:
                        continue

                    output_dir = Path(AppConfig.VERIF_PILLS)
                    output_dir.mkdir(parents=True, exist_ok=True)
                    filename = f"{pill_name}_{bay}_{x}_{y}.png"
                    save_path = output_dir / filename
                    cv2.imwrite(str(save_path), pill_crop)

                    bg_root = Path(AppConfig.BACKGROUND_IMAGES)
                    background, _ = self.get_random_background(
                        bg_root, (img_w, img_h))
                    bg_rgba = cv2.cvtColor(background, cv2.COLOR_BGR2BGRA)

                    mask_inv = cv2.bitwise_not(mask_resized)
                    mask_inv_rgb = cv2.cvtColor(mask_inv, cv2.COLOR_GRAY2BGR)

                    pill_only = cv2.bitwise_and(frame, frame, mask=mask)
                    bg_only = cv2.bitwise_and(background, mask_inv_rgb)

                    overlay = cv2.add(pill_only, bg_only)

                    output_dir = Path(AppConfig.VERIF_BACKGROUNDS)
                    output_dir.mkdir(parents=True, exist_ok=True)
                    filename = f"{pill_name}_{bay}_{x}_{y}_bg.jpg"
                    save_path = output_dir / filename
                    cv2.imwrite(str(save_path), overlay)

                    detected_medications[bay].append(Medication(
                        pill_name=pill_name,
                        count=1
                    ))

            bays_result = []
            for bay in bay_names:
                expected = self.recipe.medications.get(bay, [])
                found = detected_medications.get(bay, [])

                match = (
                    len(expected) == len(found) and
                    all(e.pill_name == f.pill_name for e,
                        f in zip(expected, found))
                )

                bays_result.append({
                    "bay": bay,
                    "expected": [m.dict() for m in expected],
                    "found": [m.dict() for m in found],
                    "match": match
                })

            verification_passed = all(bay["match"] for bay in bays_result)

            return {
                "status": True,
                "bays": bays_result,
                "verification_passed": verification_passed
            }

        except Exception as e:
            logger.error(f"Verification failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Verification failed: {str(e)}"
            )
