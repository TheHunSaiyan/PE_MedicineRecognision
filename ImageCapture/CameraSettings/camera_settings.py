import cv2
import os
import time

from datetime import datetime
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse, FileResponse
from typing import Dict, Any

from Config.config import AppConfig
from Logger.logger import logger
from Models.led_parameters import LEDParameters


class CameraSettings:
    def __init__(self, camera_controller, led_controller):
        """Initialize the CameraSettings with camera and LED controllers.

        Args: 
            camera_controller (CameraController): The controller for camera operations.
            led_controller (LEDController): The controller for LED operations.

        Returns:
            None
        """
        self.camera = camera_controller
        self.led = led_controller

    async def video_feed(self):
        """
        Generate a video feed from the camera.

        Args:
            None

        Returns:
            StreamingResponse: A streaming response that yields frames from the camera.
        """
        def generate():
            """
            Generate frames from the camera for video streaming.

            Args:
                None

            Yields:
                bytes: Encoded JPEG frames for streaming.
            """
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
        """
        Capture an image from the camera and save it with a timestamp.

        Args:
            None

        Returns:
            Dict[str, Any]: A dictionary containing the status and filename of the captured image.
        """
        frame = self.camera.get_frame()
        if frame is None:
            logger.error("No frame available")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No frame available"
            )

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
        filename = f"{AppConfig.CAPTURED_IMAGES_DIR}/{timestamp}.jpg"
        cv2.imwrite(filename, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
        logger.info(f"Image saved: {filename}")

        return {
            "status": "success",
            "filename": filename.split("/")[-1]
        }

    async def get_camera_settings(self) -> Dict[str, Any]:
        """
        Retrieve the current camera settings.

        Args:
            None

        Returns:
            Dict[str, Any]: A dictionary containing the current camera parameters.
        """
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
        """
        Update the camera settings with the provided parameters.

        Args:
            params (CameraParameters): The new camera parameters to apply.

        Returns:
            Dict[str, Any]: A dictionary indicating the success of the operation.
        """
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
        """
        Update the LED settings with the provided parameters.

        Args:
            params (LEDParameters): The new LED parameters to apply.

        Returns:
            Dict[str, Any]: A dictionary indicating the success of the operation.
        """
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
        """
        Retrieve the current LED settings.

        Args:
            None

        Returns:
            Dict[str, Any]: A dictionary containing the current LED parameters.
        """
        try:
            params = LEDParameters.load_from_file()
            return params.dict()
        except Exception as e:
            logger.error(f"Failed to get camera settings: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get camera settings: {str(e)}"
            )
