from fastapi import FastAPI, HTTPException, UploadFile, File, status, Body
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
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

from jwtbearer import JWTBearer
from Controllers.camera_controller import CameraController
from Manager.calibration_manager import CalibrationManager
from Controllers.led_controller import LEDController
from Models.led_parameters import LEDParameters
from Models.camera_parameters import CameraParameters
from Models.camera_calibration_parameters import CameraCalibrationParameters
from Models.user import User
from Models.roles import Role
from Config.config import AppConfig

from ImageCapture.CameraSettings.camera_settings import CameraSettings
from ImageCapture.CaptureCalibration.capturecalibration import CaptureCalibration
from ImageCapture.CalibrationSettings.calibration_settings import CalibrationSettings
from ImageCapture.CapturePill.capture_pill import CapturePill
from Logger.logger import logger
from DataPreparation.SplitDataset.splitdataset import SplitDataset
from DataPreparation.AugmentImage.augment_image import AugmentImage
from DataPreparation.StreamImage.stream_image import StreamImage
from DataPreparation.KFoldSort.kfoldsort import KFoldSort
from DataPreparation.RemapAnnotation.remapannotation import RemapAnnotation
from DispenseVerification.dispenseverification import DispenseVerification
from Database.database import Database
from Manager.user_manager import UserManager

security = JWTBearer()

class APIServer:
    def __init__(self):
        self.app = FastAPI()
        self.camera = CameraController()
        self.led = LEDController(port=os.path.join("/dev/", "ttyACM0"), baud=115200)
        self.calibration_manager = CalibrationManager()
        self.lock = threading.Lock()
        self.setup_middleware()
        self.setup_routes()
        self.camera_settings = CameraSettings(self.camera, self.led)
        self.capture_calibration = CaptureCalibration(self.camera, self.led)
        self.calibration_settings = CalibrationSettings(self.calibration_manager)
        self.capture_pill = CapturePill(self.camera)
        self.splitdataset = SplitDataset()
        self.augment_image = AugmentImage()
        self.stream_image = StreamImage()
        self.kfoldsort = KFoldSort()
        self.remapannotation = RemapAnnotation()
        self.dispenseverification = DispenseVerification(self.camera, self.led)
        self.database = Database()
        self.user_manager = UserManager(self.database)

    def setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["Content-Disposition"]
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
        
        @self.app.post("/create_capture_directory")
        async def create_capture_directory():
            return await self.capture_calibration.create_capture_directory()
        
        @self.app.post("/capture_calibration_image")
        async def capture_calibration_image():
            return await self.capture_calibration.capture_calibration_image()

        @self.app.post("/calibrate")
        async def update_camera_settings(params: CameraParameters):
            return await self.camera_settings.update_camera_settings(params)
        
        @self.app.post("/led_control")
        async def led_control(params: LEDParameters):
            return await self.camera_settings.led_control(params)
        
        @self.app.get("/led_settings")
        async def led_settings():
            return await self.camera_settings.led_settings()

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
        
        @self.app.get("/data_availability_for_split")
        async def get_data_availability():
            return await self.splitdataset.get_data_availability()
        
        @self.app.post("/start_split")
        async def start_split(data: Dict[str, Any]):
            return await run_in_threadpool(self.splitdataset.start_split, data)
        
        @self.app.get("/get_split_progress")
        async def get_split_progress():
            return await self.splitdataset.get_progress()
        
        @self.app.post("/stop_split")
        async def stop_split():
            return await self.splitdataset.stop_split()
        
        @self.app.get("/data_availability_for_augmentation")
        async def get_data_availability():
            return await self.augment_image.get_data_availability()
        
        @self.app.post("/start_augmentation")
        async def start_augmentation(data: Dict[str, Any]):
            return await run_in_threadpool(self.augment_image.start_augmentation, data)

        @self.app.get("/get_augmentation_progress")
        async def get_au_progress():
            return await self.augment_image.get_progress()
        
        @self.app.post("/stop_augmentation")
        async def stop_augmentation():
            return await self.augment_image.stop_augmentation()
        
        @self.app.get("/data_availability_for_stream_images")
        async def get_data_availability():
            return await self.stream_image.get_data_availability()
        
        @self.app.post("/split_consumer_reference")
        async def split_consumer_refernce():
            return await self.stream_image.split_consumer_reference()
        
        @self.app.post("/change_background")
        async def change_background():
            return await self.stream_image.change_background()
        
        @self.app.post("/start_stream_images")
        async def start_stream_images(data: Dict[str, Any]):
            return await run_in_threadpool(self.stream_image.start_stream_images, data)
        
        @self.app.get("/get_stream_image_progress")
        async def get_stream_image_progress():
            return await self.stream_image.get_progress()
        
        @self.app.post("/get_fold")
        async def get_fold(data: Dict[str, Any]):
            return await self.kfoldsort.get_fold(data)
        
        @self.app.post("/start_sort")
        async def start_sort(data: Dict[str, Any]):
            threading.Thread(target=self.kfoldsort.start_sorting, args=(data,), daemon=True).start()
            return {"message": "Sorting started"}
        
        @self.app.get("/get_sort_process")
        async def get_sort_process():
            return await self.kfoldsort.get_sort_progress()
        
        @self.app.post("/start_remap_annotation")
        async def start_remap(files: List[UploadFile] = File(...)):
            return await self.remapannotation.start_remap(files)
        
        @self.app.get("/get_remap_annotation_progress")
        async def get_progress():
            return await self.remapannotation.get_progress()
        
        @self.app.post("/initialization")
        async def initialization():
            return await self.dispenseverification.initialization()
        
        @self.app.post("/check_environment")
        async def verify_check_environment(data: Dict[str, Any]):
            return await self.dispenseverification.check_environment(data.get("holder_id", ""))
        
        @self.app.post("/attempt_login")
        async def attempt_login(data: Dict[str, Any]):
            return await self.user_manager.login(data)
        
        @self.app.get("/get_all_users")
        async def get_all_users():
            return await self.user_manager.get_all_users()
        
        @self.app.post("/create_user")
        async def create_user(data: Dict[str, Any]):
            return await self.user_manager.create_user(data)
        
        @self.app.post("/update_user")
        async def update_user(data: Dict[str, Any]):
            return await self.user_manager.update_user(data)
        
        @self.app.post("/delete_user")
        async def delete_user(user_id: str = Body(...)):
            return await self.user_manager.delete_user(user_id)

    def run(self, host: str = "0.0.0.0", port: int = 2076):
        import uvicorn
        logger.info("Starting FastAPI server...")
        uvicorn.run(self.app, host=host, port=port)

if __name__ == "__main__":
    server = APIServer()
    server.run()