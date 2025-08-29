import concurrent.futures
import cv2
import json
import numpy as np
import os
import shutil
import time
import threading

from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, Response, UploadFile, File, status, Body
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from io import BytesIO
from jwtbearer import JWTBearer
from pathlib import Path
from typing import List, Optional, Dict, Any

from Config.config import AppConfig
from Controllers.camera_controller import CameraController
from Controllers.led_controller import LEDController
from Database.database import Database
from DataPreparation.SplitDataset.splitdataset import SplitDataset
from DataPreparation.AugmentImage.augment_image import AugmentImage
from DataPreparation.StreamImage.stream_image import StreamImage
from DataPreparation.KFoldSort.kfoldsort import KFoldSort
from DataPreparation.RemapAnnotation.remapannotation import RemapAnnotation
from DispenseVerification.dispenseverification import DispenseVerification
from ImageCapture.CameraSettings.camera_settings import CameraSettings
from ImageCapture.CaptureCalibration.capturecalibration import CaptureCalibration
from ImageCapture.CalibrationSettings.calibration_settings import CalibrationSettings
from ImageCapture.CapturePill.capture_pill import CapturePill
from Logger.logger import logger
from Manager.calibration_manager import CalibrationManager
from Manager.user_manager import UserManager
from Models.led_parameters import LEDParameters
from Models.camera_parameters import CameraParameters
from Models.camera_calibration_parameters import CameraCalibrationParameters
from Models.user import User
from Models.roles import Role

security = JWTBearer()


class APIServer:
    def __init__(self):
        """
        Initialize the FastAPI server with necessary components and configurations.
        This includes setting up the camera, LED controller, calibration manager,
        and various data preparation and verification components.

        Args:
            None

        Returns:
            None
        """
        self.app = FastAPI()
        self.camera = CameraController()
        self.led = LEDController(port=os.path.join(
            "/dev/", "ttyACM0"), baud=115200)
        self.calibration_manager = CalibrationManager()
        self.lock = threading.Lock()
        self.setup_middleware()
        self.setup_routes()
        self.camera_settings = CameraSettings(self.camera, self.led)
        self.capture_calibration = CaptureCalibration(self.camera, self.led)
        self.calibration_settings = CalibrationSettings(
            self.calibration_manager)
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
        """
        Set up middleware for CORS and static file serving.
        This allows the API to handle requests from different origins
        and serve static files like captured images.

        Args:
            None

        Returns:
            None
        """
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:2077"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"]
        )

        self.app.mount(
            "/captured-images",
            StaticFiles(directory=AppConfig.CAPTURED_IMAGES_DIR),
            name="captured-images"
        )

        self.app.mount(
            "/CalibrationImages",
            StaticFiles(directory="/app/CalibrationImages"),
            name="CalibrationImages"
        )

        self.app.mount(
            "/verif_images", StaticFiles(directory=Path("/app/Verif_Images")), name="verif_images")

    def setup_routes(self):
        """
        Set up the API routes for various functionalities such as camera control,
        LED control, calibration, image capture, data preparation, dispense verification
        and user management.
        Each route is associated with a specific function that handles the request.

        Args:
            None

        Returns:
            None
        """
        @self.app.on_event("startup")
        async def startup_event():
            """
            Initialize the server components on startup.

            Args:
                None

            Returns:
                None
            """
            try:
                self.camera.start_capture()
                logger.info("Camera started successfully")
            except Exception as e:
                logger.error(f"Failed to start camera: {str(e)}")
                raise

        @self.app.on_event("shutdown")
        async def shutdown_event():
            """
            Clean up resources on shutdown, such as stopping the camera.

            Args:
                None

            Returns:
                None
            """
            self.camera.stop_capture()
            logger.info("Camera stopped")

        @self.app.post("/attempt_login")
        async def attempt_login(data: Dict[str, Any], response: Response, request: Request):
            """
            Handle user login attempts.

            Args:
                data (Dict[str, Any]): The login data containing email and password.
                response (Response): The response object to set cookies.
                request (Request): The request object to access session data.

            Returns:
                JSONResponse: A response indicating the success or failure of the login attempt.
            """
            try:
                result = await self.user_manager.login(data)
                print(f"Login successful: {result}")
                return JSONResponse(content=result)
            except HTTPException as e:
                print(f"Login error: {str(e)}")
                return JSONResponse(
                    status_code=e.status_code,
                    content={"detail": e.detail},
                    headers={
                        "Access-Control-Allow-Credentials": "true",
                        "Access-Control-Allow-Origin": "http://localhost:2077"
                    }
                )

        @self.app.post("/logout")
        async def logout(response: Response, request: Request):
            """
            Handle user logout by invalidating the session and clearing cookies.

            Args:
                response (Response): The response object to set cookies.
                request (Request): The request object to access session data.

            Returns:
                JSONResponse: A response indicating the success of the logout operation.
            """
            session_id = request.cookies.get("session_id")
            if session_id:
                self.user_manager.session_manager.invalidate_session(
                    session_id)
            response.delete_cookie("session_id")
            return {"status": "success"}

        @self.app.get("/check_session")
        async def check_session(request: Request):
            """
            Check if the user session is valid.

            Args:
                request (Request): The request object to access session data.

            Returns:
                Dict[str, Any]: A dictionary containing user ID and role if session is valid.
            """
            session_id = request.cookies.get("session_id")
            if not session_id:
                raise HTTPException(
                    status_code=401, detail="Not authenticated")

            session_data = self.user_manager.session_manager.validate_session(
                session_id)
            if not session_data:
                raise HTTPException(status_code=401, detail="Invalid session")

            return {
                "user_id": session_data.get("user_id"),
                "role": session_data.get("role")
            }

        @self.app.get("/video_feed")
        async def video_feed():
            """
            Stream video feed from the camera.

            Args:
                None

            Returns:
                StreamingResponse: A response that streams the video feed.
            """
            return await self.camera_settings.video_feed()

        @self.app.get("/capture")
        async def capture_image():
            """
            Capture an image from the camera.

            Args:
                None

            Returns:
                JSONResponse: A response containing the captured image data.
            """
            return await self.camera_settings.capture_image()

        @self.app.get("/camera_settings")
        async def get_camera_settings():
            """
            Get the current camera settings.

            Args:
                None

            Returns:
                Dict[str, Any]: A dictionary containing the camera settings.
            """
            return await self.camera_settings.get_camera_settings()

        @self.app.post("/create_capture_directory")
        async def create_capture_directory():
            """
            Create a directory for capturing images.

            Args:
                None

            Returns:
                Dict[str, Any]: A dictionary indicating the success of the operation.
            """
            return await self.capture_calibration.create_capture_directory()

        @self.app.post("/capture_calibration_image")
        async def capture_calibration_image():
            """
            Capture an image for calibration purposes.

            Args:
                None

            Returns:
                Dict[str, Any]: A dictionary containing the captured image data.
            """
            return await self.capture_calibration.capture_calibration_image()

        @self.app.post("/calibrate")
        async def update_camera_settings(params: CameraParameters):
            """
            Update the camera settings based on the provided parameters.

            Args:
                params (CameraParameters): The parameters to update the camera settings.

            Returns:
                Dict[str, Any]: A dictionary indicating the success of the operation.
            """
            return await self.camera_settings.update_camera_settings(params)

        @self.app.post("/led_control")
        async def led_control(params: LEDParameters):
            """
            Control the LED settings based on the provided parameters.

            Args:
                params (LEDParameters): The parameters to control the LED settings.

            Returns:
                Dict[str, Any]: A dictionary indicating the success of the operation.
            """
            return await self.camera_settings.led_control(params)

        @self.app.get("/led_settings")
        async def led_settings():
            """
            Get the current LED settings.

            Args:
                None

            Returns:
                Dict[str, Any]: A dictionary containing the LED settings.
            """
            return await self.camera_settings.led_settings()

        @self.app.get("/camera_calibration_parameters")
        async def get_camera_calibration_parameters():
            """
            Get the current camera calibration parameters.

            Args:
                None

            Returns:
                Dict[str, Any]: A dictionary containing the camera calibration parameters.
            """
            return await self.calibration_settings.get_camera_calibration_settings()

        @self.app.post("/camera_calibration_parameters")
        async def update_camera_calibration_parameters(params: CameraCalibrationParameters):
            """
            Update the camera calibration parameters based on the provided parameters.

            Args:
                params (CameraCalibrationParameters): The parameters to update the camera calibration settings.

            Returns:
                Dict[str, Any]: A dictionary indicating the success of the operation.
            """
            return await self.calibration_settings.update_camera_calibration_parameters(params)

        @self.app.post("/upload_calibration_images")
        async def upload_calibration_images(files: List[UploadFile] = File(...)):
            """
            Upload calibration images for camera calibration.

            Args:
                files (List[UploadFile]): A list of uploaded files containing calibration images.

            Returns:
                FileResponse: An NPZ file containing the camera calibration matrix.
            """
            return await self.calibration_settings.upload_calibration_images(files)

        @self.app.post("/generate_new_matrix_file")
        async def generate_new_matrix_file():
            """
            Generate a new camera calibration matrix file.

            Args:
                None

            Returns:
                FileResponse: An NPZ file containing the new camera calibration matrix.
            """
            return await self.calibration_settings.generate_new_matrix_file()

        @self.app.post("/undistort_image")
        async def undistort_image():
            """
            Undistort images using the camera calibration parameters.

            Args:
                None

            Returns:
                Dict[str, Any]: A dictionary indicating the success of the operation.
            """
            return await self.calibration_settings.undistort_images()

        @self.app.post("/upload_camera_calibration_npz")
        async def upload_camera_calibration_npz(file: UploadFile = File(...)):
            """
            Upload a camera calibration file in NPZ format.

            Args:
                file (UploadFile): The uploaded NPZ file containing camera calibration data.

            Returns:
                Dict[str, Any]: A dictionary indicating the success of the operation.
            """
            return await self.calibration_settings.upload_camera_calibtration(file)

        @self.app.post("/upload_undistorted_npz")
        async def upload_undistorted_npz(file: UploadFile = File(...)):
            """
            Upload an undistorted camera calibration file in NPZ format.

            Args:
                file (UploadFile): The uploaded NPZ file containing undistorted camera calibration data.

            Returns:
                Dict[str, Any]: A dictionary indicating the success of the operation.
            """
            return await self.calibration_settings.upload_undistorted(file)

        @self.app.get("/pills")
        async def get_pills():
            """
            Get the list of captured pills.

            Args:
                None

            Returns:
                JSON: A JSON response containing the list of captured pills.
            """
            return await self.capture_pill.get_pills()

        @self.app.post("/capture_pill")
        async def capture_with_metadata(data: Dict[str, Any]):
            """
            Capture a pill image with metadata.

            Args:
                data (Dict[str, Any]): The metadata for the pill capture, including pill name, lamp position, and pill side.

            Returns:
                Dict[str, Any]: A dictionary containing the status and details of the captured image.
            """
            return await self.capture_pill.capture_with_metadata(data)

        @self.app.get("/data_availability_for_split")
        async def get_data_availability():
            """
            Get the data availability for splitting datasets.

            Args:
                None

            Returns:
                Dict[str, Any]: A dictionary containing the data availability status.
            """
            return await self.splitdataset.get_data_availability()

        @self.app.post("/start_split")
        async def start_split(data: Dict[str, Any]):
            """
            Start the dataset splitting process.

            Args:
                data (Dict[str, Any]): The parameters for the dataset splitting process.

            Returns:
                Dict[str, Any]: A dictionary indicating the success of the operation.
            """
            return await run_in_threadpool(self.splitdataset.start_split, data)

        @self.app.get("/get_split_progress")
        async def get_split_progress():
            """
            Get the progress of the dataset splitting process.

            Args:
                None

            Returns:
                Dict[str, Any]: A dictionary containing the progress of the dataset splitting.
            """
            return await self.splitdataset.get_progress()

        @self.app.post("/stop_split")
        async def stop_split():
            """
            Stop the dataset splitting process.

            Args:
                None

            Returns:
                Dict[str, Any]: A dictionary indicating the success of the operation.
            """
            return await self.splitdataset.stop_split()

        @self.app.get("/data_availability_for_augmentation")
        async def get_data_availability():
            """
            Get the data availability for image augmentation.

            Args:
                None

            Returns:
                Dict[str, Any]: A dictionary containing the data availability status.
            """
            return await self.augment_image.get_data_availability()

        @self.app.post("/start_augmentation")
        async def start_augmentation(data: Dict[str, Any]):
            """
            Start the image augmentation process.

            Args:
                data (Dict[str, Any]): The parameters for the image augmentation process.

            Returns:
                Dict[str, Any]: A dictionary indicating the success of the operation.
            """
            return await run_in_threadpool(self.augment_image.start_augmentation, data)

        @self.app.get("/get_augmentation_progress")
        async def get_au_progress():
            """
            Get the progress of the image augmentation process.

            Args:
                None

            Returns:
                Dict[str, Any]: A dictionary containing the progress of the image augmentation.
            """
            return await self.augment_image.get_progress()

        @self.app.post("/stop_augmentation")
        async def stop_augmentation():
            """
            Stop the image augmentation process.

            Args:
                None

            Returns:
                Dict[str, Any]: A dictionary indicating the success of the operation.
            """
            return await self.augment_image.stop_augmentation()

        @self.app.get("/data_availability_for_stream_images")
        async def get_data_availability():
            """
            Get the data availability for streaming images.

            Args:
                None

            Returns:
                Dict[str, Any]: A dictionary containing the data availability status.
            """
            return await self.stream_image.get_data_availability()

        @self.app.post("/split_consumer_reference")
        async def split_consumer_refernce():
            """
            Split images to consumer reference for streaming images.

            Args:
                None

            Returns:
                Dict[str, Any]: A dictionary containing the split consumer reference.
            """
            return await self.stream_image.split_consumer_reference()

        @self.app.post("/change_background")
        async def change_background():
            """
            Remove the background for the split/conumser images.

            Args:
                None

            Returns:
                Dict[str, Any]: A dictionary indicating the success of the operation.
            """
            return await self.stream_image.change_background()

        @self.app.post("/start_stream_images")
        async def start_stream_images(data: Dict[str, Any]):
            """
            Start the streaming of images.

            Args:
                data (Dict[str, Any]): The parameters for the image streaming process.

            Returns:
                Dict[str, Any]: A dictionary indicating the success of the operation.
            """
            return await run_in_threadpool(self.stream_image.start_stream_images, data)

        @self.app.get("/get_stream_image_progress")
        async def get_stream_image_progress():
            """
            Get the progress of the image streaming process.

            Args:
                None

            Returns:
                Dict[str, Any]: A dictionary containing the progress of the image streaming.
            """
            return await self.stream_image.get_progress()

        @self.app.post("/stop_stream_image")
        async def stop_stream_image():
            """
            Stop the current image streaming process.

            Args:
                None

            Returns:
                None
            """
            return await self.stream_image.stop_stream_image()

        @self.app.post("/get_fold")
        async def get_fold(data: Dict[str, Any]):
            """
            Get the current K-Fold data.

            Args:
                data (Dict[str, Any]): The parameters for the K-Fold sorting process.

            Returns:
                Dict[str, Any]: A dictionary containing the K-Fold data.
            """
            return await self.kfoldsort.get_fold(data)

        @self.app.post("/start_sort")
        async def start_sort(data: Dict[str, Any]):
            """
            Start the K-Fold sorting process.

            Args:
                data (Dict[str, Any]): The parameters for the K-Fold sorting process.

            Returns:
                Dict[str, Any]: A dictionary indicating the success of the operation.
            """
            threading.Thread(target=self.kfoldsort.start_sorting,
                             args=(data,), daemon=True).start()
            return {"message": "Sorting started"}

        @self.app.get("/get_sort_process")
        async def get_sort_process():
            """
            Get the progress of the K-Fold sorting process.

            Args:
                None

            Returns:
                Dict[str, Any]: A dictionary containing the progress of the K-Fold sorting.
            """
            return await self.kfoldsort.get_sort_progress()

        @self.app.post("/stop_sort")
        async def stop_sort():
            """
            Stop the current sorting process.

            Args:
                None

            Returns:
                None
            """
            return await self.kfoldsort.stop_sort()

        @self.app.post("/start_remap_annotation")
        async def start_remap(files: List[UploadFile] = File(...), mode: Optional[str] = Body(None)):
            """
            Start the remapping of annotations for object detection or segmentation.

            Args:
                files (List[UploadFile]): A list of uploaded files containing annotations.
                mode (Optional[str]): The mode for remapping, either 'objectdetection' or 'segmentation'.

            Returns:
                Dict[str, Any]: A dictionary indicating the success of the operation.
            """
            return await self.remapannotation.start_remap(files, mode)

        @self.app.get("/get_remap_annotation_progress")
        async def get_progress():
            """
            Get the progress of the remapping of annotations.

            Args:
                None

            Returns:
                Dict[str, Any]: A dictionary containing the progress of the remapping.
            """
            return await self.remapannotation.get_progress()

        @self.app.post("/stop_remap_annotation")
        async def stop_remap_annotation():
            """
            Stop the current remap annotation.

            Args:
                None

            Returns:
                None
            """
            return await self.remapannotation.stop_remap_annotation()

        @self.app.post("/initialization")
        async def initialization():
            """
            Initialize the dispense verification system.

            Args:
                None

            Returns:
                Dict[str, Any]: A dictionary indicating the success of the initialization.
            """
            return await self.dispenseverification.initialization()

        @self.app.post("/check_environment")
        async def verify_check_environment(image: UploadFile = File(...)):
            """
            Check the environment for dispense verification.

            Args:
                data (Dict[str, Any]): The data containing the holder ID.

            Returns:
                Dict[str, Any]: A dictionary containing the result of the environment check.
            """
            return await self.dispenseverification.check_environment(image)

        @self.app.post("/selected_recipe")
        async def selected_recipe(data: Dict[str, Any]):
            """
            Store a selected medication recipe for dispensing.

            Args:
                data: Medication recipe data in the format:
                    {
                        "medications": {
                            "dispensing_bay_1": [
                                {"pill_name": "medication_name", "count": 5},
                                ...
                            ],
                            "dispensing_bay_2": [...],
                            ...
                        }
                    }

            Returns:
                dict: Status message and recipe summary
            """
            return await self.dispenseverification.selected_recipe(data)

        @self.app.post("/get_recipe_reference_images")
        async def get_recipe_reference_images(recipe_data: dict = None):
            """
            Get reference images for all pills in the current recipe.

            Args:
                None

            Returns:
                dict: Reference images for all pills in the recipe
            """
            return await self.dispenseverification.get_recipe_reference_images(recipe_data)

        @self.app.get("/get_pill_images/{pill_name}")
        async def get_pill_images(pill_name: str):
            """
            Get reference images for a specific pill.

            Args:
                pill_name (str): The name of the pill

            Returns:
                dict: Reference images for the specified pill
            """
            return await self.dispenseverification.get_recipe_reference_images(pill_name)

        @self.app.post("/verify_dispense")
        async def verify_dispense(image: UploadFile = File(...)):
            """
            Verify dispense by analyzing an uploaded image

            Args:
                image: The image file to analyze

            Returns:
                JSON response with verification results
            """
            return await self.dispenseverification.verify_dispense(image)

        @self.app.get("/get_all_users")
        async def get_all_users():
            """
            Get all users from the database.

            Args:
                None

            Returns:
                List[User]: A list of User objects representing all users in the database.
            """
            return await self.user_manager.get_all_users()

        @self.app.post("/create_user")
        async def create_user(data: Dict[str, Any]):
            """
            Create a new user in the database.

            Args:
                data (Dict[str, Any]): The user data containing first name, last name, email, password, and role.

            Returns:
                Dict[str, Any]: A dictionary containing the status and details of the created user.
            """
            return await self.user_manager.create_user(data)

        @self.app.post("/update_user")
        async def update_user(data: Dict[str, Any]):
            """
            Update an existing user in the database.

            Args:
                data (Dict[str, Any]): The user data containing user ID, first name, last name, email, password, and role.

            Returns:
                Dict[str, Any]: A dictionary containing the status and details of the updated user.
            """
            return await self.user_manager.update_user(data)

        @self.app.post("/delete_user")
        async def delete_user(data: Dict[str, Any]):
            """
            Delete a user from the database.

            Args:
                data (Dict[str, Any]): The user data containing the user ID.

            Returns:
                Dict[str, Any]: A dictionary containing the status and details of the deleted user.
            """
            return await self.user_manager.delete_user(data.get("user_id", ""))

    def run(self, host: str = "0.0.0.0", port: int = 2076):
        """
        Run the FastAPI server.

        Args:
            host (str): The host address to run the server on. 
            port (int): The port number to run the server on.

        Returns:
            None
        """
        import uvicorn
        logger.info("Starting FastAPI server...")
        uvicorn.run(self.app, host=host, port=port)


if __name__ == "__main__":
    """
    Main entry point to run the API server.
    """
    server = APIServer()
    server.run()
