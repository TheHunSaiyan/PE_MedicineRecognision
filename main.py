from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import cv2
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:2077"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/captured-images", StaticFiles(directory="CapturedImages"), name="captured-images")

@app.get("/capture")
async def root():
    cam = cv2.VideoCapture('/dev/video2', cv2.CAP_V4L2)

    if not cam.isOpened():
        return {"error": "Failed to open /dev/video2"}

    ret, frame = cam.read()
    cam.release()
    filename = "CapturedImages/"+datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f") + ".png"

    if ret:
        cv2.imwrite(filename, frame)
        print(f'Image captured and saved as {filename}')
        cam.release()
        return {
            "status": "success",
            "filename": filename.split("/")[-1]
        }
    else:
        cam.release()
        return {"status": "error", "error": "Failed to capture image"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=2076)