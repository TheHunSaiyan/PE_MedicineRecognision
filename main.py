from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import cv2
from datetime import datetime
import threading
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:2077"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/captured-images", StaticFiles(directory="CapturedImages"), name="captured-images")

# Shared frame and thread lock
latest_frame = None
lock = threading.Lock()

def camera_reader():
    global latest_frame
    print("Starting camera reader...")

    cam = cv2.VideoCapture('/dev/video2', cv2.CAP_V4L2)  # Try /dev/video0 first
    if not cam.isOpened():
        print("ERROR: Failed to open /dev/video0")
        return

    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("Camera opened successfully")

    frame_count = 0

    while True:
        ret, frame = cam.read()
        if not ret:
            print("⚠️ Failed to read frame")
            time.sleep(0.1)
            continue

        with lock:
            latest_frame = frame

        frame_count += 1
        if frame_count % 30 == 0:
            print("✅ Frame updated")

        time.sleep(0.05)

# Start the camera thread
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

if __name__ == "__main__":
    import uvicorn
    print("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=2076)
