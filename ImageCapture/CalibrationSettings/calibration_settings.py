import cv2
import numpy as np
import os

from datetime import datetime
from fastapi import HTTPException, status
from fastapi.responses import FileResponse
from io import BytesIO

from Config.config import AppConfig
from Logger.logger import logger

class CalibrationSettings:
    def __init__(self, calibration_manager):
        self.calibration_manager = calibration_manager
    
    async def get_camera_calibration_settings(self):
        params = self.calibration_manager.load_calibration_parameters()
        if params is None:
            logger.error("Camera calibration parameters not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Camera calibration parameters not found"
            )
        return params.dict()
    
    async def update_camera_calibration_parameters(self, params):
        try:
            self.calibration_manager.save_calibration_parameters(params)
            return {
                "status": "success", 
                "message": "Camera calibration parameters saved successfully"
            }
        except ValueError as e:
            logger.error(str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Failed to save calibration parameters: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save calibration parameters: {str(e)}"
            )
            
    async def upload_calibration_images(self, files):
        try:
            if not self.calibration_manager.load_calibration_parameters():
                logger.error("Calibration parameters not configured")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Calibration parameters not configured"
                )
            
            image_points = []
            object_points = []
            good_files = 0
            saved_images = []
            original_images = []
    
            for file in files:
                try:
                    filename = os.path.basename(file.filename)
                    file_path = os.path.join(AppConfig.CALIBRATION_IMAGES_DIR, filename)
                    
                    with open(file_path, "wb") as buffer:
                        buffer.write(await file.read())
                    
                    src = cv2.imread(file_path)
                    if src is None:
                        os.remove(file_path)
                        continue
                    
                    grey = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
                    ret, corners = cv2.findChessboardCorners(
                        grey, 
                        (self.calibration_manager.calibration_params.chess_col, self.calibration_manager.calibration_params.chess_row), 
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
                    logger.warning(f"Error processing {filename}: {str(e)}")
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    continue
    
            if good_files == 0:
                logger.error("No valid calibration images found. Could not detect chessboard in any image.")
                raise HTTPException(
                    status_code=400, 
                    detail="No valid calibration images found. Could not detect chessboard in any image."
                )
    
            objp = np.zeros((self.calibration_manager.calibration_params.chess_row * self.calibration_manager.calibration_params.chess_col, 3), np.float32)
            objp[:, :2] = np.mgrid[0:self.calibration_manager.calibration_params.chess_col, 0:self.calibration_manager.calibration_params.chess_row].T.reshape(-1, 2)
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
                logger.error("Camera calibration failed")
                raise HTTPException(
                    status_code=500, 
                    detail="Camera calibration failed"
                )
    
            cam_mtx_filename = "Data/NPZ/camera_calibration_params.npz"
            np.savez(
                cam_mtx_filename,
                camera_matrix=camera_matrix,
                distortion_coefficients=dist_coefficients,
                rotation_vectors=rvecs,
                translation_vectors=tvecs,
                object_points=object_points,
                image_points=image_points,
                original_image_paths=np.array(saved_images),
                source_images=AppConfig.CALIBRATION_IMAGES_DIR,
            )
    
            return FileResponse(
                cam_mtx_filename,
                media_type="application/octet-stream",
                filename=cam_mtx_filename,
                headers={
                    "message": f"Calibration completed with {good_files} good files and {len(files) - good_files} bad files.",
                    "reprojection_error": str(ret),
                    "source_images": AppConfig.CALIBRATION_IMAGES_DIR
                }
            )
    
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during calibration: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Unexpected error during calibration: {str(e)}"
            )
            
    async def generate_new_matrix_file(self):
        try:
            calibration_data = np.load("Data/NPZ/camera_calibration_params.npz", allow_pickle=True)
            
            required_keys = [
                'camera_matrix', 'distortion_coefficients', 
                'object_points', 'rotation_vectors',
                'translation_vectors', 'image_points',
                'original_image_paths'
            ]
            
            for key in required_keys:
                if key not in calibration_data:
                    logger.error(f"Missing required data in calibration file: {key}")
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
                logger.error("No original images found in calibration data")
                raise HTTPException(
                    status_code=400,
                    detail="No original images found in calibration data"
                )
    
            first_image_path = original_image_paths[0]
            first_image = cv2.imread(first_image_path)
            if first_image is None:
                logger.error(f"Could not read first calibration image at {first_image_path}")
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
                logger.error("Could not calculate reprojection error - no valid projections")
                raise HTTPException(
                    status_code=500,
                    detail="Could not calculate reprojection error - no valid projections"
                )
    
            errors = error_count / valid_projections
            
            if errors > self.calibration_manager.calibration_params.error_threshold:
                logger.error(f"Calibration error too high: {errors:.2f}. Please check your images.")
                raise HTTPException(
                    status_code=500,
                    detail=f"Calibration error too high: {errors:.2f}. Please check your images.",
                )
            
            np.savez(
        "Data/NPZ/undistorted_camera_matrix.npz",
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
                "Data/NPZ/undistorted_camera_matrix.npz",
                media_type="application/octet-stream",
                filename="Data/NPZ/undistorted_camera_matrix.npz",
                headers={
                    "message": "New matrix file generated successfully.",
                    "reprojection_error": str(errors),
                    "source_images": str("Data/CalibrationImages")
                }
            )
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error generating new matrix file: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Error generating new matrix file: {str(e)}"
            )
            
    async def undistort_images(self):
        try:
            calibration_data = np.load("Data/NPZ/undistorted_camera_matrix.npz")
    
            camera_matrix = np.ascontiguousarray(calibration_data['camera_matrix'])
            dist_coefficients = np.ascontiguousarray(calibration_data['distortion_coefficients'])
            undistorted_camera_matrix = np.ascontiguousarray(calibration_data['undistorted_camera_matrix'])
            roi = calibration_data['roi']
            original_image_paths = calibration_data['original_image_paths']
    
            undistorted_dir = "Data/UndistortedImages"
            os.makedirs(undistorted_dir, exist_ok=True)
    
            undistorted_images = []
            for img_path in original_image_paths:
                try:
                    img = cv2.imread(img_path)
                    if img is None:
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
                    logger.warning(str(e))
                    continue
    
            if not undistorted_images:
                logger.error("No images were successfully undistorted")
                raise HTTPException(
                    status_code=500,
                    detail="No images were successfully undistorted"
                )
            
            return {
                "status": "success",
                "message": f"Undistorted {len(undistorted_images)} images successfully."
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error undistorting images: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error undistorting images: {str(e)}"
            )
            
    async def upload_camera_calibtration(self, file):
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
                    logger.error(f"Missing required data in calibration file: {key}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Missing required data in calibration file: {key}"
                    )
            
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            output_filename = f"Data/NPZ/camera_calibration_params_{timestamp}.npz"
            
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
            logger.error(f"Failed to process calibration file: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process calibration file: {str(e)}"
            )
        
    async def upload_undistorted(self, file):
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
            
            for key in required_keys:
                if key not in calibration_data:
                    logger.error(f"Missing required data in undistorted matrix file: {key}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Missing required data in undistorted matrix file: {key}"
                    )
            
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            output_filename = f"Data/NPZ/undistorted_camera_matrix_{timestamp}.npz"
            
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
            logger.error(f"Failed to process undistorted matrix file: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process undistorted matrix file: {str(e)}"
            )