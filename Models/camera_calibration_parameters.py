import json
import os

from typing import Optional
from pydantic import BaseModel

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
    def load_from_file(cls, filename: str = "Data/JSON/camera_calibration_params.json") -> Optional['CameraCalibrationParameters']:
        if not os.path.exists(filename):
            return None
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            return cls(**data)
        except Exception as e:
            print(f"Error loading config: {e}")
            return None
        
    def save_to_file(self, filename: str = "Data/JSON/camera_calibration_params.json"):
        with open(filename, 'w') as f:
            json.dump(self.dict(), f, indent=4)