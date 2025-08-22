import glob
import os
from pathlib import Path
from typing import Any, Dict, List

from fastapi import File, Form, HTTPException, UploadFile, status

from Config.config import AppConfig
from Controllers.camera_controller import CameraController
from Controllers.led_controller import LEDController
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

    async def check_environment(self, holder_id: str):
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

        result = await self.verification_manager.analyze_environment(holder_id)
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
