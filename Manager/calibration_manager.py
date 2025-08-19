import cv2
import json
import numpy as np
import os

from pathlib import Path
from typing import List, Optional, Tuple

from Config.config import AppConfig
from Models.camera_calibration_parameters import CameraCalibrationParameters


class CalibrationManager:
    def __init__(self):
        """
        Initialize the CalibrationManager instance.

        Args:
            None

        Returns:
            None
        """
        self.calibration_params: Optional[CameraCalibrationParameters] = None
        self.calibration_data = None

    def load_calibration_parameters(self) -> Optional[CameraCalibrationParameters]:
        """
        Load camera calibration parameters from persistent storage.

        Args:
            None

        Returns:
            Optional[CameraCalibrationParameters]: Loaded calibration parameters 
                                                  if available, None otherwise.
        """
        self.calibration_params = CameraCalibrationParameters.load_from_file()
        return self.calibration_params

    def save_calibration_parameters(self, params: CameraCalibrationParameters):
        """
        Save camera calibration parameters to persistent storage.

        Args:
            params (CameraCalibrationParameters): Calibration parameters to save.

        Returns:
            None
        """
        params.validate()
        params.save_to_file()
        self.calibration_params = params

    def process_calibration_images(self, image_paths: List[str]) -> Tuple[bool, Optional[float]]:
        """
        Process calibration images to compute camera intrinsic parameters.

        Args:
            image_paths (List[str]): List of paths to calibration images 
                                    containing chessboard patterns.

        Returns:
            Tuple[bool, Optional[float]]: 
                - bool: True if calibration succeeded, False otherwise
                - Optional[float]: Mean reprojection error if successful, None otherwise
        """
        if not self.calibration_params:
            raise ValueError("Calibration parameters not loaded")

        objp = np.zeros((self.calibration_params.chess_row *
                        self.calibration_params.chess_col, 3), np.float32)
        objp[:, :2] = np.mgrid[0:self.calibration_params.chess_col,
                               0:self.calibration_params.chess_row].T.reshape(-1, 2)

        obj_points = []
        img_points = []
        valid_images = []

        for img_path in image_paths:
            img = cv2.imread(img_path)
            if img is None:
                continue

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            ret, corners = cv2.findChessboardCorners(
                gray,
                (self.calibration_params.chess_col,
                 self.calibration_params.chess_row),
                None,
                cv2.CALIB_CB_FAST_CHECK
            )

            if ret:
                corners = cv2.cornerSubPix(
                    gray,
                    corners,
                    (11, 11),
                    (-1, -1),
                    criteria=(cv2.TERM_CRITERIA_EPS +
                              cv2.TERM_CRITERIA_COUNT, 30, 0.001)
                )
                obj_points.append(objp)
                img_points.append(corners)
                valid_images.append(img_path)

        img_size = gray.shape[::-1]
        ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
            obj_points, img_points, img_size, None, None
        )

        if not ret:
            return False, None

        mean_error = 0
        for i in range(len(obj_points)):
            img_points2, _ = cv2.projectPoints(
                obj_points[i], rvecs[i], tvecs[i], mtx, dist
            )
            error = cv2.norm(img_points[i], img_points2,
                             cv2.NORM_L2) / len(img_points2)
            mean_error += error

        mean_error /= len(obj_points)

        self.calibration_data = {
            'camera_matrix': mtx,
            'dist_coefficients': dist,
            'rvecs': rvecs,
            'tvecs': tvecs,
            'obj_points': obj_points,
            'img_points': img_points,
            'image_paths': valid_images,
            'reprojection_error': mean_error
        }

        return True, mean_error

    def generate_undistorted_matrix(self):
        """
        Generate optimal undistorted camera matrix based on calibration data.

        Args:
            None

        Returns:
            tuple: Contains:
                - new_camera_mtx (numpy.ndarray): Optimal undistorted camera matrix
                - roi (tuple): Region of interest coordinates (x, y, width, height)
        """
        if not self.calibration_data:
            raise ValueError("No calibration data available")

        img = cv2.imread(self.calibration_data['image_paths'][0])
        h, w = img.shape[:2]

        new_camera_mtx, roi = cv2.getOptimalNewCameraMatrix(
            self.calibration_data['camera_matrix'],
            self.calibration_data['dist_coefficients'],
            (w, h),
            1,
            (w, h)
        )

        self.calibration_data.update({
            'undistorted_camera_matrix': new_camera_mtx,
            'roi': roi
        })

        return new_camera_mtx, roi

    def save_calibration_data(self, filename: str):
        """
        Save calibration data to a JSON file.

        Args:
            filename (str): Path to the output JSON file.

        Returns:
            None
        """
        if not self.calibration_data:
            raise ValueError("No calibration data to save")

        data_to_save = {
            key: value.tolist() if isinstance(value, np.ndarray) else value
            for key, value in self.calibration_data.items()
        }

        with open(filename, 'w') as f:
            json.dump(data_to_save, f, indent=4)

    def undistort_image(self, img_path: str, output_dir: str = None) -> Optional[str]:
        """
        Apply camera calibration to undistort an image.

        Args:
            img_path (str): Path to the input image to undistort.
            output_dir (str, optional): Directory to save undistorted image.
                                       Defaults to AppConfig.UNDISTORTED_IMAGES_DIR.

        Returns:
            Optional[str]: Path to the saved undistorted image if successful,
                          None if input image cannot be read.
        """
        if not self.calibration_data or 'undistorted_camera_matrix' not in self.calibration_data:
            raise ValueError("Undistorted camera matrix not available")

        img = cv2.imread(img_path)
        if img is None:
            return None

        undistorted = cv2.undistort(
            img,
            self.calibration_data['camera_matrix'],
            self.calibration_data['dist_coefficients'],
            None,
            self.calibration_data['undistorted_camera_matrix']
        )

        roi = self.calibration_data.get('roi')
        if roi is not None and any(roi):
            x, y, w, h = roi
            undistorted = undistorted[y:y+h, x:x+w]

        if output_dir is None:
            output_dir = AppConfig.UNDISTORTED_IMAGES_DIR

        Path(output_dir).mkdir(exist_ok=True)
        output_path = str(Path(output_dir) / Path(img_path).name)
        cv2.imwrite(output_path, undistorted)

        return output_path
