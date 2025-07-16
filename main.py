from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import cv2
from datetime import datetime
import threading
import time
import json
import os
from pathlib import Path
from typing import Optional
import logging
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import shutil
from io import BytesIO

CONFIG_FILE = "camera_params.json"
CALI_CONFIG_FILE = "camera_calibration_params.json"

original_images = []
undistorted_camera_matrix = np.empty([3, 3])
roi = None
camera_matrix = None
dist_coefficients = None
object_points = []
rotation_vectors = []
translation_vectors = []
image_points = []

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:2077"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/captured-images", StaticFiles(directory="CapturedImages"), name="captured-images")

latest_frame = None

class CameraCalibrationParameters(BaseModel):
    chess_row: int = 7
    chess_col: int = 6
    square_size: float = 10
    error_threshold: float = 0.5

    def validate(self):
        if not (1 <= self.chess_row):
            raise ValueError("Chessboard rows must be higher than 1")
        if not (1 <= self.chess_col):
            raise ValueError("Chessboard columns must be higher than 1")
        if self.square_size <= 0:
            raise ValueError("Square size must be a positive number")
        if not (0 < self.error_threshold <= 1):
            raise ValueError("Error threshold must be between 0 and 1")
    
    @classmethod
    def load_from_file(cls) -> Optional['CameraCalibrationParameters']:
        if not os.path.exists(CALI_CONFIG_FILE):
            return None
        try:
            with open(CALI_CONFIG_FILE, 'r') as f:
                data = json.load(f)
            return cls(**data)
        except Exception as e:
            print(f"Error loading config: {e}")
            return None
        
    def save_to_file(self):
        with open(CALI_CONFIG_FILE, 'w') as f:
            json.dump(self.dict(), f, indent=4)

class CameraParameters(BaseModel):
    brightness: int = 0
    contrast: int = 32
    saturation: int = 60
    white_balance_automatic: bool = False
    white_balance_temperature: int = 4600
    sharpness: int = 2
    auto_exposure: int = 1
    exposure_time_absolute: int = 157
    exposure_dynamic_framerate: bool = False

    def validate(self):
        if not (-64 <= self.brightness <= 64):
            raise ValueError("Brightness must be between -64 and 64")
        if not (0 <= self.contrast <= 64):
            raise ValueError("Contrast must be between 0 and 64")
        if not (0 <= self.saturation <= 128):
            raise ValueError("Saturation must be between 0 and 128")
        if not (2800 <= self.white_balance_temperature <= 6500):
            raise ValueError("White balance temperature must be between 2800 and 6500")
        if not (0 <= self.sharpness <= 6):
            raise ValueError("Sharpness must be between 0 and 6")
        if not (0 <= self.auto_exposure <= 3):
            raise ValueError("Auto exposure must be between 0 and 3")
        if not (1 <= self.exposure_time_absolute <= 5000):
            raise ValueError("Exposure time absolute must be between 1 and 5000")
        
    @classmethod
    def load_from_file(cls) -> Optional['CameraParameters']:
        if not os.path.exists(CONFIG_FILE):
            return None
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
            return cls(**data)
        except Exception as e:
            print(f"Error loading config: {e}")
            return None
    
    def save_to_file(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.dict(), f, indent=4)

cam = None
lock = threading.Lock()
cam_lock = threading.Lock()
CalibrationParameters = CameraCalibrationParameters.load_from_file()

def camera_reader():
    global latest_frame, cam
    print("Starting camera reader...")

    saved_config = CameraParameters.load_from_file()

    cam = cv2.VideoCapture('/dev/video2', cv2.CAP_V4L2)
    if not cam.isOpened():
        print("ERROR: Failed to open /dev/video0")
        return

    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if saved_config:
        print("Applying saved camera configuration")
        apply_camera_parameters(cam, saved_config)
    else:
        print("No saved configuration found, using defaults")

    print("Camera opened successfully")

    frame_count = 0

    while True:
        ret, frame = cam.read()
        if not ret:
            print("Failed to read frame")
            time.sleep(0.1)
            continue

        with lock:
            latest_frame = frame

        frame_count += 1
        if frame_count % 30 == 0:
            print("Frame updated")

        time.sleep(0.05)

threading.Thread(target=camera_reader, daemon=True).start()

@app.get("/video_feed")
def video_feed():
    def generate_video():
        global latest_frame
        while True:
            with lock:
                frame = latest_frame.copy() if latest_frame is not None else None
            if frame is None:
                time.sleep(0.1)
                continue
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.05)

    return StreamingResponse(generate_video(), media_type='multipart/x-mixed-replace; boundary=frame')

@app.get("/capture")
async def capture():
    global latest_frame
    with lock:
        frame = latest_frame.copy() if latest_frame is not None else None

    if frame is None:
        print("ERROR: No frame available when capture requested")
        return {"status": "error", "error": "No frame available"}

    filename = "CapturedImages/" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f") + ".png"
    cv2.imwrite(filename, frame)
    print(f"Image saved: {filename}")
    return {"status": "success", "filename": filename.split("/")[-1]}

def apply_camera_parameters(camera, params: CameraParameters):
    try:
        params.validate()
    except ValueError as e:
        print(f"Invalid parameters: {e}")
        return False

    try:
        cam.set(cv2.CAP_PROP_BRIGHTNESS, params.brightness)
        cam.set(cv2.CAP_PROP_CONTRAST, params.contrast)
        cam.set(cv2.CAP_PROP_SATURATION, params.saturation)
        cam.set(cv2.CAP_PROP_AUTO_WB, float(params.white_balance_automatic))  
        cam.set(cv2.CAP_PROP_WB_TEMPERATURE, params.white_balance_temperature)
        cam.set(cv2.CAP_PROP_SHARPNESS, params.sharpness)   
        cam.set(cv2.CAP_PROP_AUTO_EXPOSURE, params.auto_exposure)    
        cam.set(cv2.CAP_PROP_EXPOSURE, params.exposure_time_absolute)
        return True
    except Exception as e:
        print(f"Error applying camera parameters: {e}")
        return False

@app.get("/camera_settings")
async def get_camera_settings():
    global cam
    if cam is None:
        raise HTTPException(status_code=503, detail="Camera not initialized")

    with cam_lock:
        try:
            params = CameraParameters(
                brightness=int(cam.get(cv2.CAP_PROP_BRIGHTNESS)),
                contrast=int(cam.get(cv2.CAP_PROP_CONTRAST)),
                saturation=int(cam.get(cv2.CAP_PROP_SATURATION)),
                white_balance_automatic=bool(cam.get(cv2.CAP_PROP_AUTO_WB)),
                white_balance_temperature=int(cam.get(cv2.CAP_PROP_WB_TEMPERATURE)),
                sharpness=int(cam.get(cv2.CAP_PROP_SHARPNESS)),
                auto_exposure=int(cam.get(cv2.CAP_PROP_AUTO_EXPOSURE)),
                exposure_time_absolute=int(cam.get(cv2.CAP_PROP_EXPOSURE))
            )
            return params.dict()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get camera settings: {str(e)}")

@app.post("/calibrate/")
async def calibrate(input_params: CameraParameters):
    global cam
    try:
        input_params.validate()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    if cam is None:
        raise HTTPException(status_code=503, detail="Camera not initialized")

    with cam_lock:
        try:
            if apply_camera_parameters(cam, input_params):
                input_params.save_to_file()
                CalibrationParameters = input_params
                return {"status": "success", "message": "Camera parameters updated and saved"}
            else:
                raise HTTPException(status_code=500, detail="Failed to apply some camera parameters")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to set camera parameters: {str(e)}")
        
@app.get("/camera_calibration_parameters")
async def get_camera_calibration_parameters():
    data = CameraCalibrationParameters.load_from_file()
    if data is None:
        raise HTTPException(status_code=404, detail="Camera calibration parameters not found")
    return data.dict()

@app.post("/camera_calibration_parameters")
async def camera_calibration_parameters(input_params: CameraCalibrationParameters):
    try:
        input_params.validate()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    input_params.save_to_file()
    return {"status": "success", "message": "Camera calibration parameters saved successfully"}

image_size = None

def corner(self, i, img):
    try:
        src = cv2.imdecode(np.frombuffer(img.read(), np.uint8), cv2.IMREAD_COLOR)
        grey = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)

        if image_size is None:
            image_size = grey.shape[:2]

        data = CameraParameters.load_from_file()
        if data is None:
            raise ValueError("Camera calibration parameters not found")
        
        ret, corners = cv2.findChessboardCorners(grey, (data['chess_col'], data['chess_row']), None, cv2.CALIB_CB_FAST_CHECK)
        if ret:
            corners = cv2.cornerSubPix(grey, corners, (11, 11), (-1, -1), criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, 30, 0.001))
            return corners, src
        else:
            return None, src
    except Exception as e:
        logging.error(f"Error finding corners in image {i}: {str(e)}")
        return None, img

@app.post("/upload_calibration_images")
async def upload_folder(files: List[UploadFile] = File(...)):
    try:
        logger.info(f"Received {len(files)} files in the folder")
        
        if not os.path.exists("camera_calibration_params.json"):
            raise HTTPException(status_code=400, detail="Calibration parameters file not found")
        
        with open("camera_calibration_params.json", 'r') as f:
            data = json.load(f)

        calib_images_dir = "CalibrationImages"
    
        if os.path.exists(calib_images_dir):
            shutil.rmtree(calib_images_dir)
        os.makedirs(calib_images_dir, exist_ok=True)

        image_points = []
        object_points = []
        good_files = 0
        saved_images = []
        original_images = []

        for file in files:
            try:
                filename = os.path.basename(file.filename)
                file_path = os.path.join(calib_images_dir, filename)
                
                with open(file_path, "wb") as buffer:
                    buffer.write(await file.read())
                
                src = cv2.imread(file_path)
                if src is None:
                    logger.warning(f"Could not read image {filename}")
                    os.remove(file_path)
                    continue
                
                grey = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
                ret, corners = cv2.findChessboardCorners(
                    grey, 
                    (data['chess_col'], data['chess_row']), 
                    None, 
                    cv2.CALIB_CB_FAST_CHECK
                )
                
                if ret:
                    corners = cv2.cornerSubPix(
                        grey, 
                        corners, 
                        (11, 11), 
                        (-1, -1), 
                        criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, 30, 0.001)
                    )
                    image_points.append(corners)
                    original_images.append(src)
                    saved_images.append(file_path)
                    good_files += 1
                else:
                    logger.warning(f"Chessboard not found in {filename}")
                    os.remove(file_path)
            except Exception as e:
                logger.error(f"Error processing {filename}: {str(e)}")
                if os.path.exists(file_path):
                    os.remove(file_path)
                continue

        if good_files == 0:
            raise HTTPException(
                status_code=400, 
                detail="No valid calibration images found. Could not detect chessboard in any image."
            )

        objp = np.zeros((data['chess_row'] * data['chess_col'], 3), np.float32)
        objp[:, :2] = np.mgrid[0:data['chess_col'], 0:data['chess_row']].T.reshape(-1, 2)
        object_points = [objp] * len(image_points)

        grey = cv2.cvtColor(original_images[0], cv2.COLOR_BGR2GRAY)
        image_size = grey.shape[::-1]

        ret, camera_matrix, dist_coefficients, rvecs, tvecs = cv2.calibrateCamera(
            objectPoints=object_points,
            imagePoints=image_points,
            imageSize=image_size,
            cameraMatrix=None,
            distCoeffs=None
        )

        if not ret:
            raise HTTPException(
                status_code=500, 
                detail="Camera calibration failed"
            )

        cam_mtx_filename = "camera_calibration_params.npz"
        np.savez(
            cam_mtx_filename,
            camera_matrix=camera_matrix,
            distortion_coefficients=dist_coefficients,
            rotation_vectors=rvecs,
            translation_vectors=tvecs,
            object_points=object_points,
            image_points=image_points,
            original_image_paths=np.array(saved_images),
            source_images=calib_images_dir,
        )

        return FileResponse(
            cam_mtx_filename,
            media_type="application/octet-stream",
            filename=cam_mtx_filename,
            headers={
                "message": f"Calibration completed with {good_files} good files and {len(files) - good_files} bad files.",
                "reprojection_error": str(ret),
                "source_images": calib_images_dir
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during calibration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Unexpected error during calibration: {str(e)}"
        )

@app.post("/generate_new_matrix_file")
async def generate_new_matrix_file():
    try:
        if not os.path.exists("camera_calibration_params.npz"):
            raise HTTPException(status_code=404, detail="Calibration file not found")

        calibration_data = np.load("camera_calibration_params.npz", allow_pickle=True)
        
        required_keys = [
            'camera_matrix', 'distortion_coefficients', 
            'object_points', 'rotation_vectors',
            'translation_vectors', 'image_points',
            'original_image_paths'
        ]
        
        for key in required_keys:
            if key not in calibration_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required data in calibration file: {key}"
                )

        camera_matrix = np.ascontiguousarray(calibration_data['camera_matrix'])
        dist_coefficients = np.ascontiguousarray(calibration_data['distortion_coefficients'])
        object_points = np.ascontiguousarray(calibration_data['object_points'])
        rotation_vectors = np.ascontiguousarray(calibration_data['rotation_vectors'])
        translation_vectors = np.ascontiguousarray(calibration_data['translation_vectors'])
        image_points = np.ascontiguousarray(calibration_data['image_points'])
        original_image_paths = calibration_data['original_image_paths']

        if len(original_image_paths) == 0:
            raise HTTPException(
                status_code=400,
                detail="No original images found in calibration data"
            )

        first_image_path = original_image_paths[0]
        first_image = cv2.imread(first_image_path)
        if first_image is None:
            raise HTTPException(
                status_code=400,
                detail=f"Could not read first calibration image at {first_image_path}"
            )
            
        height, width = first_image.shape[:2]

        undistorted_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(
            camera_matrix.astype(np.float64),
            dist_coefficients.astype(np.float64),
            (width, height),
            1,
            (width, height),
        )

        error_count = 0
        valid_projections = 0
        
        for i in range(len(object_points)):
            if (i >= len(rotation_vectors)) or (i >= len(translation_vectors)):
                continue
                
            image_points2, _ = cv2.projectPoints(
                object_points[i],
                rotation_vectors[i],
                translation_vectors[i],
                camera_matrix,
                dist_coefficients,
            )
            
            if len(image_points2) == 0:
                continue
                
            error = cv2.norm(image_points[i], image_points2, cv2.NORM_L2) / len(image_points2)
            error_count += error
            valid_projections += 1

        if valid_projections == 0:
            raise HTTPException(
                status_code=500,
                detail="Could not calculate reprojection error - no valid projections"
            )

        errors = error_count / valid_projections
        
        if errors > CalibrationParameters.error_threshold:
            raise HTTPException(
                status_code=500,
                detail=f"Calibration error too high: {errors:.2f}. Please check your images.",
            )
        
        np.savez(
    "undistorted_camera_matrix.npz",
    camera_matrix=camera_matrix,
    distortion_coefficients=dist_coefficients,
    undistorted_camera_matrix=undistorted_camera_matrix,
    roi=roi,
    rotation_vectors=rotation_vectors,
    translation_vectors=translation_vectors,
    object_points=object_points,
    image_points=image_points,
    original_image_paths=original_image_paths
)
        
        return FileResponse(
            "undistorted_camera_matrix.npz",
            media_type="application/octet-stream",
            filename="undistorted_camera_matrix.npz",
            headers={
                "message": "New matrix file generated successfully.",
                "reprojection_error": str(errors),
                "source_images": str("CalibrationImages")
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating new matrix file: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Error generating new matrix file: {str(e)}"
        )

@app.post("/undistort_image")
async def undistort_image():
    try:
        if not os.path.exists("undistorted_camera_matrix.npz"):
            raise HTTPException(status_code=404, detail="Calibration file not found")
        
        calibration_data = np.load("undistorted_camera_matrix.npz")
        
        camera_matrix = np.ascontiguousarray(calibration_data['camera_matrix'])
        dist_coefficients = np.ascontiguousarray(calibration_data['distortion_coefficients'])
        undistorted_camera_matrix = np.ascontiguousarray(calibration_data['undistorted_camera_matrix'])
        roi = calibration_data['roi']
        original_image_paths = calibration_data['original_image_paths']

        undistorted_dir = "UndistortedImages"
        os.makedirs(undistorted_dir, exist_ok=True)

        undistorted_images = []
        for img_path in original_image_paths:
            try:
                img = cv2.imread(img_path)
                if img is None:
                    logger.warning(f"Could not read image: {img_path}")
                    continue
                undistorted_img = cv2.undistort(
                    img,
                    camera_matrix,
                    dist_coefficients,
                    None,
                    undistorted_camera_matrix
                )

                if roi is not None and roi.any():
                    x, y, w, h = roi
                    undistorted_img = undistorted_img[y:y+h, x:x+w]

                filename = os.path.basename(img_path)
                output_path = os.path.join(undistorted_dir, filename)
                cv2.imwrite(output_path, undistorted_img)
                undistorted_images.append(output_path)

            except Exception as e:
                logger.error(f"Error processing {img_path}: {str(e)}")
                continue

        if not undistorted_images:
            raise HTTPException(
                status_code=500,
                detail="No images were successfully undistorted"
            )
        
        return {
            "status": "success",
            "message": f"Undistorted {len(undistorted_images)} images successfully.",
            "undistorted_images": undistorted_images
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error undistorting images: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error undistorting images: {str(e)}"
        )

@app.post("/upload_camera_calibration_npz")
async def upload_camera_calibration_npz(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        
        npz_file = BytesIO(contents)
        
        calibration_data = np.load(npz_file, allow_pickle=True)
        
        required_keys = [
            'camera_matrix', 'distortion_coefficients', 
            'rotation_vectors', 'translation_vectors',
            'object_points', 'image_points',
            'original_image_paths'
        ]
        
        for key in required_keys:
            if key not in calibration_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required data in calibration file: {key}"
                )
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_filename = f"camera_calibration_params_{timestamp}.npz"
        
        np.savez(
            output_filename,
            camera_matrix=calibration_data['camera_matrix'],
            distortion_coefficients=calibration_data['distortion_coefficients'],
            rotation_vectors=calibration_data['rotation_vectors'],
            translation_vectors=calibration_data['translation_vectors'],
            object_points=calibration_data['object_points'],
            image_points=calibration_data['image_points'],
            original_image_paths=calibration_data['original_image_paths']
        )
        
        return {
            "status": "success",
            "message": "Camera calibration file uploaded and saved successfully",
            "filename": output_filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing calibration file: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing calibration file: {str(e)}"
        )

@app.post("/upload_undistorted_npz")
async def upload_undistorted_npz(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        
        npz_file = BytesIO(contents)
        
        calibration_data = np.load(npz_file, allow_pickle=True)
        
        required_keys = [
            'camera_matrix', 
            'distortion_coefficients',
            'undistorted_camera_matrix',
            'roi',
            'rotation_vectors',
            'translation_vectors',
            'object_points',
            'image_points'
        ]

        print("Keys in uploaded file:", list(calibration_data.keys()))
        
        for key in required_keys:
            if key not in calibration_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required data in undistorted matrix file: {key}"
                )
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_filename = f"undistorted_camera_matrix_{timestamp}.npz"
        
        np.savez(
            output_filename,
            camera_matrix=calibration_data['camera_matrix'],
            distortion_coefficients=calibration_data['distortion_coefficients'],
            undistorted_camera_matrix=calibration_data['undistorted_camera_matrix'],
            roi=calibration_data['roi'],
            rotation_vectors=calibration_data['rotation_vectors'],
            translation_vectors=calibration_data['translation_vectors'],
            object_points=calibration_data['object_points'],
            image_points=calibration_data['image_points'],
            original_image_paths=calibration_data.get('original_image_paths', [])
        )
        
        return {
            "status": "success",
            "message": "Undistorted camera matrix file uploaded and saved successfully",
            "filename": output_filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing undistorted matrix file: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing undistorted matrix file: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    print("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=2076)
