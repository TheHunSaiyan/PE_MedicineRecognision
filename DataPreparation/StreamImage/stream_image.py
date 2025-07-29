import os

from typing import Dict, List, Tuple

from Config.config import AppConfig

class StreamImage():
    
    async def get_data_availability(self):
        return {
            "images": os.path.exists(AppConfig.DATASET_IMAGES) and bool(os.listdir(AppConfig.DATASET_IMAGES)),
            "mask_images": os.path.exists(AppConfig.DATASET_MASKS) and bool(os.listdir(AppConfig.DATASET_MASKS)),
            "split": True,
            "background_changed": True
        }
        
    async def start_stream_images(self, data: Dict[str, any]):
        pass
    
    async def get_progress(self):
        pass