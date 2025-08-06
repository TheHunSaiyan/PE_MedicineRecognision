import json
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any

import cv2
from ultralytics import YOLO

from Controllers.camera_controller import CameraController
from Controllers.led_controller import LEDController
from Logger.logger import logger
from Config.config import AppConfig


class VerificationManager:
    def __init__(self, camera: CameraController, led: LEDController):
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
        try:
            self.geometry = await self._initialize_geometry_file()
            self.model = await self._initialize_model()
            self.initialized = True
            return True
        except Exception as e:
            logger.error(f"Verification initialization failed: {str(e)}")
            return False

    async def _initialize_geometry_file(self) -> Optional[Dict]:
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

    async def analyze_environment(self, expected_holder_id: str, lamp_mode: str = "upper") -> Dict[str, Any]:
        if not self.initialized:
            return {"status": False, "message": "Verification system not initialized"}

        try:
            brightness = 100 if lamp_mode == "upper" else 80
            pin = 11 if lamp_mode == "upper" else 9
            self.led.set_values(brightness, pin)
            
            frame = self.camera.get_frame()
            if frame is None:
                raise RuntimeError("Failed to capture frame")
            
            results = self.model(frame)
            predicted_label = results[0].names[results[0].probs.top1]

            if predicted_label != "tray":
                return {
                    "status": False,
                    "message": "Tray not detected"
                }

            qr_detector = cv2.QRCodeDetector()
            retval, decoded_qrs, points, _ = qr_detector.detectAndDecodeMulti(frame)

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