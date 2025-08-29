import cv2
import json
import logging
import os

from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import File, UploadFile
import numpy as np
from ultralytics import YOLO

from Config.config import AppConfig
from Controllers.camera_controller import CameraController
from Controllers.led_controller import LEDController
from Logger.logger import logger


class VerificationManager:
    def __init__(self, camera: CameraController, led: LEDController):
        """
        Initialize the VerificationManager with camera and LED controllers.

        Args:
            camera (CameraController): Controller for camera operations.
            led (LEDController): Controller for LED lighting control.

        Returns:
            None
        """
        self.camera = camera
        self.led = led
        self.unanticipated_object = False
        self.model: Optional[YOLO] = None
        self.geometry: Optional[Dict] = None
        self.initialized = False

        self.slot_mapping = {
            0: "morning",
            1: "noon",
            2: "evening",
            3: "night"
        }

    async def initialize(self):
        """
        Initialize the verification system components.

        Args:
            None

        Returns:
            bool: True if initialization succeeded, False otherwise.
        """
        try:
            self.geometry = await self._initialize_geometry_file()
            self.model = await self._initialize_model()
            self.initialized = True
            return True
        except Exception as e:
            logger.error(f"Verification initialization failed: {str(e)}")
            return False

    async def _initialize_geometry_file(self) -> Optional[Dict]:
        """
        Load geometry configuration from JSON file.

        Args:
            None

        Returns:
            Optional[Dict]: Geometry configuration dictionary if successful,
                           None if file not found or invalid.
        """
        geometry_path = AppConfig.GEOMETRY_COORDS
        geometry_file = os.path.join(geometry_path, "geometry.json")

        if not os.path.isfile(geometry_file):
            logger.error(f"Geometry file not found: {geometry_file}")
            return None

        try:
            with open(geometry_file, "r") as json_file:
                return json.load(json_file)
        except Exception as e:
            logger.error(f"Failed to load geometry file: {str(e)}")
            return None

    async def _initialize_model(self) -> Optional[YOLO]:
        """
        Load YOLO object detection model from weights file.

        Args:
            None

        Returns:
            Optional[YOLO]: Initialized YOLO model instance if successful,
                           None if model file not found or invalid.
        """
        model_path = AppConfig.ENVIRONMENT_WEIGHTS
        latest_model_file = os.path.join(model_path, "yolov11n_env.pt")

        if not os.path.isfile(latest_model_file):
            logger.error("No YOLO model file found")
            return None

        try:
            return YOLO(latest_model_file)
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {str(e)}")
            return None

    async def _read_uploaded_image(self, image: UploadFile) -> Optional[np.ndarray]:
        """
        Read and decode an uploaded image file.

        Args:
            image (UploadFile): The uploaded image file

        Returns:
            Optional[np.ndarray]: Decoded image as numpy array, or None if failed
        """
        try:
            contents = await image.read()

            nparr = np.frombuffer(contents, np.uint8)

            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None:
                logger.error("Failed to decode uploaded image")
                return None

            return frame

        except Exception as e:
            logger.error(f"Error reading uploaded image: {str(e)}")
            return None

    async def _check_tray_content(self, img: np.ndarray, min_contour_area: int = 10,
                                  kernel_size: int = 7, low_thresh: int = 1,
                                  high_thresh: int = 120) -> bool:
        """
        Check if objects are present in specified holder spaces on a tray.

        Args:
            img: The input image of the tray.
            min_contour_area: The minimum contour area to consider as an object.
            kernel_size: The size of the GaussianBlur kernel for image smoothing.
            low_thresh: The lower threshold for the Canny edge detection.
            high_thresh: The higher threshold for the Canny edge detection.

        Returns:
            bool: True if tray is empty (no objects detected in any holder space), False otherwise.
        """
        if self.geometry is None:
            logger.error("Geometry configuration not loaded")
            return False

        temp_list = []
        for holder_space in self.geometry.get('holder_spaces', []):
            polygon_points = [(p.get("x", 0), p.get("y", 0))
                              for p in holder_space.get('polygon', [])]
            polygon_points = np.array(polygon_points).astype(int)

            x, y, w, h = cv2.boundingRect(polygon_points)

            roi = img[y:y + h, x:x + w]

            gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

            blurred_roi = cv2.GaussianBlur(
                gray_roi, (kernel_size, kernel_size), 0)

            edges = cv2.Canny(blurred_roi, low_thresh, high_thresh)

            contours, _ = cv2.findContours(
                edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            object_detected = any(cv2.contourArea(
                contour) > min_contour_area for contour in contours)
            temp_list.append(object_detected)

        return not any(temp_list)

    async def analyze_environment(self, image: UploadFile = File(...), expected_holder_id: str = "123456789", lamp_mode: str = "upper") -> Dict[str, Any]:
        """
        Analyze the dispensing environment for verification readiness using an uploaded image.

        Args:
            image (UploadFile): The uploaded image file to analyze
            expected_holder_id (str): Expected QR code value for validation.
            lamp_mode (str, optional): Lighting mode - "upper" or "side".
                                     Defaults to "upper".

        Returns:
            Dict[str, Any]: Analysis results.
        """
        if not self.initialized:
            return {"status": False, "message": "Verification system not initialized"}

        try:
            frame = await self._read_uploaded_image(image)
            if frame is None:
                return {"status": False, "message": "Failed to read uploaded image"}

            results = self.model(frame)
            predicted_label = results[0].names[results[0].probs.top1]

            if predicted_label != "tray":
                return {
                    "status": False,
                    "message": "Tray not detected"
                }

            qr_detector = cv2.QRCodeDetector()
            retval, decoded_qrs, points, _ = qr_detector.detectAndDecodeMulti(
                frame)

            if not retval or not decoded_qrs:
                return {
                    "status": False,
                    "message": "QR code not detected"
                }

            _, frame_width, _ = frame.shape
            qr_x_position = points[0][0][0]
            center_x = frame_width // 2

            if qr_x_position < center_x:
                return {
                    "status": False,
                    "message": "QR code on wrong side"
                }

            if decoded_qrs[0] != expected_holder_id:
                return {
                    "status": False,
                    "message": f"QR code mismatch. Expected {expected_holder_id}, got {decoded_qrs[0]}"
                }

            is_empty = await self._check_tray_content(frame)
            if not is_empty:
                return {
                    "status": False,
                    "message": "Tray is not empty"
                }

            return {"status": True, "message": "Environment ready for verification"}

        except Exception as e:
            logger.error(f"Environment analysis failed: {str(e)}")
            return {
                "status": False,
                "message": f"Analysis error: {str(e)}"
            }
