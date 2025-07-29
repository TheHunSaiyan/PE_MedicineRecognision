import cv2
import threading
import time

from typing import Optional
from Config.config import AppConfig
from Models.camera_parameters import CameraParameters

class CameraController:
    def __init__(self, video_source: str = '/dev/video2'):
        self.video_source = video_source
        self.camera: Optional[cv2.VideoCapture] = None
        self.latest_frame = None
        self.lock = threading.Lock()
        self.cam_lock = threading.Lock()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
    def start_capture(self):
        if self.running:
            return
            
        saved_config = CameraParameters.load_from_file()
        
        self.camera = cv2.VideoCapture(self.video_source, cv2.CAP_V4L2)
        if not self.camera.isOpened():
            raise RuntimeError(f"Failed to open {self.video_source}")
            
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        if saved_config:
            self.apply_parameters(saved_config)
            
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        
    def stop_capture(self):
        self.running = False
        if self.thread:
            self.thread.join()
        if self.camera:
            self.camera.release()
            
    def _capture_loop(self):
        while self.running:
            ret, frame = self.camera.read()
            if not ret:
                time.sleep(0.1)
                continue
                
            with self.lock:
                self.latest_frame = frame
                
            time.sleep(0.05)
            
    def get_frame(self):
        with self.lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None
            
    def apply_parameters(self, params: CameraParameters):
        try:
            params.validate()
        except ValueError as e:
            raise ValueError(f"Invalid parameters: {e}")

        with self.cam_lock:
            try:
                self.camera.set(cv2.CAP_PROP_BRIGHTNESS, params.brightness)
                self.camera.set(cv2.CAP_PROP_CONTRAST, params.contrast)
                self.camera.set(cv2.CAP_PROP_SATURATION, params.saturation)
                self.camera.set(cv2.CAP_PROP_AUTO_WB, float(params.white_balance_automatic))
                self.camera.set(cv2.CAP_PROP_WB_TEMPERATURE, params.white_balance_temperature)
                self.camera.set(cv2.CAP_PROP_SHARPNESS, params.sharpness)
                self.camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, params.auto_exposure)
                self.camera.set(cv2.CAP_PROP_EXPOSURE, params.exposure_time_absolute)
                return True
            except Exception as e:
                raise RuntimeError(f"Error applying camera parameters: {e}")
                
    def get_current_parameters(self) -> CameraParameters:
        with self.cam_lock:
            try:
                return CameraParameters(
                    brightness=int(self.camera.get(cv2.CAP_PROP_BRIGHTNESS)),
                    contrast=int(self.camera.get(cv2.CAP_PROP_CONTRAST)),
                    saturation=int(self.camera.get(cv2.CAP_PROP_SATURATION)),
                    white_balance_automatic=bool(self.camera.get(cv2.CAP_PROP_AUTO_WB)),
                    white_balance_temperature=int(self.camera.get(cv2.CAP_PROP_WB_TEMPERATURE)),
                    sharpness=int(self.camera.get(cv2.CAP_PROP_SHARPNESS)),
                    auto_exposure=int(self.camera.get(cv2.CAP_PROP_AUTO_EXPOSURE)),
                    exposure_time_absolute=int(self.camera.get(cv2.CAP_PROP_EXPOSURE))
                )
            except Exception as e:
                raise RuntimeError(f"Failed to get camera settings: {str(e)}")