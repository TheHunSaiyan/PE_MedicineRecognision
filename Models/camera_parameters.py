import json
import os

from typing import Optional
from pydantic import BaseModel

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
    def load_from_file(cls, filename: str = "camera_params.json") -> Optional['CameraParameters']:
        if not os.path.exists(filename):
            return None
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            return cls(**data)
        except Exception as e:
            print(f"Error loading config: {e}")
            return None
    
    def save_to_file(self, filename: str = "camera_params.json"):
        with open(filename, 'w') as f:
            json.dump(self.dict(), f, indent=4)