from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from datetime import datetime
import cv2
import time
import logging
from typing import Dict, Any

from config import AppConfig

class CameraSettings:
    def __init__(self, camera_controller):
        self.camera = camera_controller

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
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No frame available"
            )
            
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
        filename = f"{AppConfig.CAPTURED_IMAGES_DIR}/{timestamp}.png"
        cv2.imwrite(filename, frame)
        
        return {
            "status": "success", 
            "filename": filename.split("/")[-1]
        }

    async def get_camera_settings(self) -> Dict[str, Any]:
        try:
            params = self.camera.get_current_parameters()
            return params.dict()
        except Exception as e:
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
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to apply some camera parameters"
                )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to set camera parameters: {str(e)}"
            )