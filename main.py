from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
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

CONFIG_FILE = "camera_params.json"

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

class CameraParameters(BaseModel):
    brightness: int = 0
    contrast: int = 32
    saturation: int = 60
    hue: int = 0
    white_balance_automatic: bool = False
    gamma: int = 100
    gain: int = 0
    power_line_frequency: int = 1
    white_balance_temperature: int = 4600
    sharpness: int = 2
    backlight_compensation: int = 1
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
        if not (-40 <= self.hue <= 40):
            raise ValueError("Hue must be between -40 and 40")
        if not (72 <= self.gamma <= 500):
            raise ValueError("Gamma must be between 72 and 500")
        if not (0 <= self.gain <= 100):
            raise ValueError("Gain must be between 0 and 100")
        if not (0 <= self.power_line_frequency <= 2):
            raise ValueError("Power line frequency must be between 0 and 2")
        if not (2800 <= self.white_balance_temperature <= 6500):
            raise ValueError("White balance temperature must be between 2800 and 6500")
        if not (0 <= self.sharpness <= 6):
            raise ValueError("Sharpness must be between 0 and 6")
        if not (0 <= self.backlight_compensation <= 2):
            raise ValueError("Backlight compensation must be between 0 and 2")
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
        cam.set(cv2.CAP_PROP_HUE, params.hue)    
        if hasattr(cv2, 'CAP_PROP_AUTO_WB'):
            cam.set(cv2.CAP_PROP_AUTO_WB, float(params.white_balance_automatic))    
        if hasattr(cv2, 'CAP_PROP_GAMMA'):
            cam.set(cv2.CAP_PROP_GAMMA, params.gamma)    
        cam.set(cv2.CAP_PROP_GAIN, params.gain)
        if hasattr(cv2, 'CAP_PROP_POWER_LINE_FREQUENCY'):
            cam.set(cv2.CAP_PROP_POWER_LINE_FREQUENCY, params.power_line_frequency)
        elif hasattr(cv2, 'CAP_PROP_IEEE1394'):
            cam.set(cv2.CAP_PROP_IEEE1394, params.power_line_frequency)    
        if hasattr(cv2, 'CAP_PROP_WB_TEMPERATURE'):
            cam.set(cv2.CAP_PROP_WB_TEMPERATURE, params.white_balance_temperature)    
        if hasattr(cv2, 'CAP_PROP_SHARPNESS'):
            cam.set(cv2.CAP_PROP_SHARPNESS, params.sharpness)    
        if hasattr(cv2, 'CAP_PROP_BACKLIGHT'):
            cam.set(cv2.CAP_PROP_BACKLIGHT, params.backlight_compensation)    
        if hasattr(cv2, 'CAP_PROP_AUTO_EXPOSURE'):
            cam.set(cv2.CAP_PROP_AUTO_EXPOSURE, params.auto_exposure)    
        if hasattr(cv2, 'CAP_PROP_EXPOSURE'):
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
                hue=int(cam.get(cv2.CAP_PROP_HUE)),
                white_balance_automatic=bool(cam.get(cv2.CAP_PROP_AUTO_WB)),
                gamma=int(cam.get(cv2.CAP_PROP_GAMMA)),
                gain=int(cam.get(cv2.CAP_PROP_GAIN)),
                white_balance_temperature=int(cam.get(cv2.CAP_PROP_WB_TEMPERATURE)),
                sharpness=int(cam.get(cv2.CAP_PROP_SHARPNESS)),
                backlight_compensation=int(cam.get(cv2.CAP_PROP_BACKLIGHT)),
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
                return {"status": "success", "message": "Camera parameters updated and saved"}
            else:
                raise HTTPException(status_code=500, detail="Failed to apply some camera parameters")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to set camera parameters: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=2076)
