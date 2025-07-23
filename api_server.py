from fastapi import FastAPI, HTTPException, UploadFile, File, status
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from io import BytesIO
from datetime import datetime
import cv2
import numpy as np
import json
import os
import shutil
import time
from typing import List, Optional, Dict, Any
from pathlib import Path
import threading
import concurrent.futures

from camera_controller import CameraController
from calibration_manager import CalibrationManager
from models import CameraParameters, CameraCalibrationParameters
from config import AppConfig

from CameraSettings.camera_settings import CameraSettings
from CalibrationSettings.calibration_settings import CalibrationSettings
from CapturePill.capture_pill import CapturePill
from logger import logger
from SplitDataset.splitdataset import SplitDataset
from AugmentImage.augment_image import AugmentImage

class APIServer:
    def __init__(self):
        self.app = FastAPI()
        self.camera = CameraController()
        self.calibration_manager = CalibrationManager()
        self.lock = threading.Lock()
        self.setup_middleware()
        self.setup_routes()
        AppConfig.ensure_directories_exist()
        self.camera_settings = CameraSettings(self.camera)
        self.calibration_settings = CalibrationSettings(self.calibration_manager)
        self.capture_pill = CapturePill(self.camera)
        self.splitdataset = SplitDataset()
        self.augment_image = AugmentImage()

    def setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:2077"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self.app.mount(
            "/captured-images", 
            StaticFiles(directory=AppConfig.CAPTURED_IMAGES_DIR), 
            name="captured-images"
        )

    def setup_routes(self):
        @self.app.on_event("startup")
        async def startup_event():
            try:
                self.camera.start_capture()
                logger.info("Camera started successfully")
            except Exception as e:
                logger.error(f"Failed to start camera: {str(e)}")
                raise

        @self.app.on_event("shutdown")
        async def shutdown_event():
            self.camera.stop_capture()
            logger.info("Camera stopped")

        @self.app.get("/video_feed")
        async def video_feed():
            return await self.camera_settings.video_feed()

        @self.app.get("/capture")
        async def capture_image():
            return await self.camera_settings.capture_image()

        @self.app.get("/camera_settings")
        async def get_camera_settings():
            return await self.camera_settings.get_camera_settings()

        @self.app.post("/calibrate")
        async def update_camera_settings(params: CameraParameters):
            return await self.camera_settings.update_camera_settings(params)

        @self.app.get("/camera_calibration_parameters")
        async def get_camera_calibration_parameters():
            return await self.calibration_settings.get_camera_calibration_settings()

        @self.app.post("/camera_calibration_parameters")
        async def update_camera_calibration_parameters(params: CameraCalibrationParameters):
            return await self.calibration_settings.update_camera_calibration_parameters(params)

        @self.app.post("/upload_calibration_images")
        async def upload_calibration_images(files: List[UploadFile] = File(...)):
            return await self.calibration_settings.upload_calibration_images(files)

        @self.app.post("/generate_new_matrix_file")
        async def generate_new_matrix_file():
            return await self.calibration_settings.generate_new_matrix_file()

        @self.app.post("/undistort_image")
        async def undistort_image():
            return await self.calibration_settings.undistort_images()

        @self.app.post("/upload_camera_calibration_npz")
        async def upload_camera_calibration_npz(file: UploadFile = File(...)):
            return await self.calibration_settings.upload_camera_calibtration(file)

        @self.app.post("/upload_undistorted_npz")
        async def upload_undistorted_npz(file: UploadFile = File(...)):
            return await self.calibration_settings.upload_undistorted(file)

        @self.app.get("/pills")
        async def get_pills():
            return await self.capture_pill.get_pills()

        @self.app.post("/capture_pill")
        async def capture_with_metadata(data: Dict[str, Any]):
            return await self.capture_pill.capture_with_metadata(data)
        
        @self.app.get("/data_availability")
        async def get_data_availability():
            return await self.splitdataset.get_data_availability()
        
        @self.app.post("/start_split")
        async def start_split(data: Dict[str, Any]):
            return await self.splitdataset.start_split(data)
        
        @self.app.post("/start_augmentation")
        async def start_augmentation(data: Dict[str, Any]):
            return await self.augment_image.start_augmentation(data)

    def run(self, host: str = "0.0.0.0", port: int = 2076):
        import uvicorn
        logger.info("Starting FastAPI server...")
        uvicorn.run(self.app, host=host, port=port)

if __name__ == "__main__":
    server = APIServer()
    server.run()