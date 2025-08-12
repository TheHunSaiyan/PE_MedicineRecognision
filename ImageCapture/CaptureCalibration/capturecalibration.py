import time
import cv2
import json
import os
from datetime import datetime
from fastapi import HTTPException, status

from Config.config import AppConfig
from Logger.logger import logger

class CaptureCalibration:
    def __init__(self, camera_controller, led_controller):
        self.camera = camera_controller
        self.led = led_controller
        self.capture_dir = None
        self.count = 0
        
    async def create_capture_directory(self):
        try:
            self.count += 1
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            capture_dir = os.path.join(AppConfig.CALIBRATION_IMAGES_DIR, timestamp)
            self.capture_dir = capture_dir
            os.makedirs(capture_dir, exist_ok=True)
            logger.info(f"Capture directory created: {capture_dir}")
            return {"status": "success", "folder_name": timestamp}
        except Exception as e:
            logger.error(f"Failed to create capture directory: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create capture directory: {str(e)}"
            )
        
    async def capture_calibration_image(self):
        try:
            led_brightness = json.load(open(AppConfig.LED_PARAMS_FILE, 'r'))['upper_led']
            self.led.set_values(led_brightness, 11)
            time.sleep(1)
            frame = self.camera.get_frame()
            if frame is None:
                logger.error("No frame available for calibration capture")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to capture image"
                )
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.count}_{timestamp}.jpg"
            self.count += 1
            filepath = os.path.join(str(self.capture_dir), filename)
            
            cv2.imwrite(filepath, frame)
            self.led.set_values(0, 11)
            logger.info(f"Calibration image saved: {filepath}")
            
            relative_path = os.path.relpath(filepath, start=AppConfig.CAPTURED_IMAGES_DIR)
        
            return {
                "status": "success",
                "filename": filename,
                "filepath": f"captured-images/{relative_path.replace('\\', '/')}"
            }
        except Exception as e:
            logger.error(f"Failed to capture calibration image: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )