import json
import os

from typing import Optional
from pydantic import BaseModel
            
class LEDParameters(BaseModel):
    upper_led: int = 50
    side_led: int = 50
    
    @classmethod
    def load_from_file(cls, filename: str = "led_params.json") -> Optional['LEDParameters']:
        if not os.path.exists(filename):
            return None
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            return cls(**data)
        except Exception as e:
            print(f"Error loading config: {e}")
            return None
    
    def save_to_file(self, filename: str = "led_params.json"):
        if self.upper_led == 0 or self.side_led == 0:
            return
        with open(filename, 'w') as f:
            json.dump(self.dict(), f, indent=4)