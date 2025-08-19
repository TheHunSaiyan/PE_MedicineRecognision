import cv2
import threading
import time

from typing import Optional

from Config.config import AppConfig
from Logger.logger import logger
from Models.camera_parameters import CameraParameters


class CameraController:
    def __init__(self, video_source: str = '/dev/video2'):
        """
        Initialize the CameraController with specified video source.

        Args:
            video_source (str): The video device path (default: '/dev/video2').

        Returns:
            None
        """
        self.video_source = video_source
        self.camera: Optional[cv2.VideoCapture] = None
        self.latest_frame = None
        self.lock = threading.Lock()
        self.cam_lock = threading.Lock()
        self.running = False
        self.thread: Optional[threading.Thread] = None

    def start_capture(self):
        """
        Start continuous frame capture from the camera.

        Args:
            None

        Returns:
            None
        """
        if self.running:
            return

        saved_config = CameraParameters.load_from_file()

        try:
            self.camera = cv2.VideoCapture(self.video_source, cv2.CAP_V4L2)
            if not self.camera.isOpened():
                raise RuntimeError(f"Failed to open {self.video_source}")

            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            if saved_config:
                self.apply_parameters(saved_config)

            self.running = True
            self.thread = threading.Thread(
                target=self._capture_loop, daemon=True)
            self.thread.start()
        except Exception as e:
            logger.error(f"Camera initialization error: {e}")

    def stop_capture(self):
        """
        Stop the continuous frame capture.

        Args:
            None

        Returns:
            None
        """
        self.running = False
        if self.thread:
            self.thread.join()
        if self.camera:
            self.camera.release()

    def _capture_loop(self):
        """
        Background thread loop for continuous frame capture.

        Args:
            None

        Returns:
            None
        """
        while self.running:
            try:
                ret, frame = self.camera.read()
                if not ret:
                    time.sleep(0.1)
                    continue

                with self.lock:
                    self.latest_frame = frame

                time.sleep(0.05)
            except Exception as e:
                logger.error(f"Error in capture loop: {e}")
                break

    def get_frame(self):
        """
        Get a copy of the latest captured frame.

        Args:
            None

        Returns:
            numpy.ndarray or None: A copy of the latest frame if available,
                                  None if no frame is available or error occurs.
        """
        with self.lock:
            try:
                return self.latest_frame.copy()
            except Exception as e:
                logger.error(f"Error copying frame: {e}")
                return None

    def apply_parameters(self, params: CameraParameters):
        """
        Apply camera parameters to the active camera.

        Args:
            params (CameraParameters): Camera parameters to apply.

        Returns:
            bool: True if parameters were applied successfully.
        """
        try:
            params.validate()
        except ValueError as e:
            raise ValueError(f"Invalid parameters: {e}")

        with self.cam_lock:
            try:
                self.camera.set(cv2.CAP_PROP_BRIGHTNESS, params.brightness)
                self.camera.set(cv2.CAP_PROP_CONTRAST, params.contrast)
                self.camera.set(cv2.CAP_PROP_SATURATION, params.saturation)
                self.camera.set(cv2.CAP_PROP_AUTO_WB, float(
                    params.white_balance_automatic))
                self.camera.set(cv2.CAP_PROP_WB_TEMPERATURE,
                                params.white_balance_temperature)
                self.camera.set(cv2.CAP_PROP_SHARPNESS, params.sharpness)
                self.camera.set(cv2.CAP_PROP_AUTO_EXPOSURE,
                                params.auto_exposure)
                self.camera.set(cv2.CAP_PROP_EXPOSURE,
                                params.exposure_time_absolute)
                return True
            except Exception as e:
                raise RuntimeError(f"Error applying camera parameters: {e}")

    def get_current_parameters(self) -> CameraParameters:
        """
        Retrieve current camera parameters.

        Args:
            None

        Returns:
            CameraParameters: Object containing current camera settings.
        """
        with self.cam_lock:
            try:
                return CameraParameters(
                    brightness=int(self.camera.get(cv2.CAP_PROP_BRIGHTNESS)),
                    contrast=int(self.camera.get(cv2.CAP_PROP_CONTRAST)),
                    saturation=int(self.camera.get(cv2.CAP_PROP_SATURATION)),
                    white_balance_automatic=bool(
                        self.camera.get(cv2.CAP_PROP_AUTO_WB)),
                    white_balance_temperature=int(
                        self.camera.get(cv2.CAP_PROP_WB_TEMPERATURE)),
                    sharpness=int(self.camera.get(cv2.CAP_PROP_SHARPNESS)),
                    auto_exposure=int(self.camera.get(
                        cv2.CAP_PROP_AUTO_EXPOSURE)),
                    exposure_time_absolute=int(
                        self.camera.get(cv2.CAP_PROP_EXPOSURE))
                )
            except Exception as e:
                raise RuntimeError(f"Failed to get camera settings: {str(e)}")
