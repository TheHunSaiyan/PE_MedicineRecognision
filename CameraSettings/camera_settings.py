from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from datetime import datetime
import cv2
import time
from typing import Dict, Any

from config import AppConfig
from logger import logger
from models import LEDParameters

class CameraSettings:
    def __init__(self, camera_controller, led_controller):
        self.camera = camera_controller
        self.led = led_controller

    async def video_feed(self):
        def generate():
            while True:
                frame = self.camera.get_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue
                    
                ret, buffer = cv2.imencode('.jpg', frame)
                if not ret:
                    continue
                    
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                time.sleep(0.05)
                
        return StreamingResponse(
            generate(), 
            media_type='multipart/x-mixed-replace; boundary=frame'
        )

    async def capture_image(self) -> Dict[str, Any]:
        frame = self.camera.get_frame()
        if frame is None:
            logger.error("No frame available")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No frame available"
            )
            
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
        filename = f"{AppConfig.CAPTURED_IMAGES_DIR}/{timestamp}.png"
        cv2.imwrite(filename, frame)
        logger.info(f"Image saved: {filename}")
        
        return {
            "status": "success", 
            "filename": filename.split("/")[-1]
        }

    async def get_camera_settings(self) -> Dict[str, Any]:
        try:
            params = self.camera.get_current_parameters()
            return params.dict()
        except Exception as e:
            logger.error(f"Failed to get camera settings: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get camera settings: {str(e)}"
            )

    async def update_camera_settings(self, params) -> Dict[str, Any]:
        try:
            if self.camera.apply_parameters(params):
                params.save_to_file()
                return {
                    "status": "success", 
                    "message": "Camera parameters updated and saved"
                }
            else:
                logger.error("Failed to apply some camera parameters")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to apply some camera parameters"
                )                
        except ValueError as e:
            logger.error(str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Failed to set camera parameters: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to set camera parameters: {str(e)}"
            )
            
    async def led_control(self, params):
        try:
            side_value = params.side_led
            upper_value = params.upper_led
            print(f"{upper_value} : {side_value}")
            
            self.led.set_values(side_value, 9)
            self.led.set_values(side_value, 10)
            self.led.set_values(upper_value, 11)
            
            params.save_to_file()
            
            return {
                "status": "success",
                "message": "LED values updated",
                "led_values": params
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        
    async def led_settings(self) -> Dict[str, Any]:
        try:
            params = LEDParameters.load_from_file()
            return params.dict()
        except Exception as e:
            logger.error(f"Failed to get camera settings: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get camera settings: {str(e)}"
            )
        