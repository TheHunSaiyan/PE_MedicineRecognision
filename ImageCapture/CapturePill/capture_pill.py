import cv2
import json
import os

from fastapi import HTTPException, status
from pathlib import Path

from Config.config import AppConfig
from Logger.logger import logger


class CapturePill:
    def __init__(self, camera_controller):
        """
        Initialize the CapturePill with a camera controller.

        Args:
            camera_controller (CameraController): The controller for camera operations.

        Returns:
            None
        """
        self.camera = camera_controller

    async def get_pills(self):
        """
        Retrieve the list of pills from the configured data file.

        Args:
            None

        Returns:
            JSON: A JSON object containing the list of pills and their details.
        """
        if not os.path.exists(AppConfig.PILLS_DATA_FILE):
            logger.error("Pills data not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pills data not found"
            )

        try:
            with open(AppConfig.PILLS_DATA_FILE, 'r') as f:
                pills_data = json.load(f)
            return pills_data
        except Exception as e:
            logger.error(f"Failed to load pills data: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to load pills data: {str(e)}"
            )

    async def capture_with_metadata(self, data):
        """
        Capture an image of a pill with metadata and save it.

        Args:
            data (dict): A dictionary containing the pill name, lamp position, and pill side.

        Returns:
            Dict[str, Any]: A dictionary containing the status and filename of the captured image.
        """
        try:
            pill_name = data.get('pill_name')
            if not pill_name:
                logger.error("Pill name is required")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Pill name is required"
                )

            lamp_position = data.get('lamp_position', 'upperLamp')
            pill_side = data.get('pill_side', 'top')

            pill_dir = Path(AppConfig.CAPTURED_IMAGES_DIR) / pill_name
            pill_dir.mkdir(parents=True, exist_ok=True)

            existing_images = list(pill_dir.glob("*.jpg"))
            next_image_number = len(existing_images)

            frame = self.camera.get_frame()
            if frame is None:
                logger.error("No frame available")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="No frame available"
                )

            filename = f"{pill_name}_{next_image_number:03d} \
            _{lamp_position[0]}_{pill_side[0]}.jpg"
            filepath = pill_dir / filename

            cv2.imwrite(str(filepath), frame, [
                        int(cv2.IMWRITE_JPEG_QUALITY), 100])

            return {
                "status": "success",
                "filename": str(filename),
                "image_number": next_image_number,
                "full_path": str(filepath)
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
