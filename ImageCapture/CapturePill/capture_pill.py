import cv2
import json
import os

from fastapi import HTTPException, status
from pathlib import Path

from Config.config import AppConfig
from Logger.logger import logger

class CapturePill:
    def __init__(self, camera_controller):
        self.camera = camera_controller
    
    async def get_pills(self):
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
            
            existing_images = list(pill_dir.glob("*.png"))
            next_image_number = len(existing_images)
            
            frame = self.camera.get_frame()
            if frame is None:
                logger.error("No frame available")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="No frame available"
                )

            filename = f"{next_image_number:04d}_{pill_name}_{lamp_position}_{pill_side}.png"
            filepath = pill_dir / filename
            
            cv2.imwrite(str(filepath), frame)
            
            return {
                "status": "success",
                "filename": str(filepath.relative_to(AppConfig.CAPTURED_IMAGES_DIR)),
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
