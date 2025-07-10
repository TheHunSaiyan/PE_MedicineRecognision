from fastapi import FastAPI
from fastapi.responses import FileResponse
import cv2
from datetime import datetime

app = FastAPI()

@app.get("/")
async def root():
    cam = cv2.VideoCapture('/dev/video2', cv2.CAP_V4L2)

    if not cam.isOpened():
        return {"error": "Failed to open /dev/video2"}

    ret, frame = cam.read()
    cam.release()
    filename = "CapturedImages/"+datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f") + ".png"

    if ret:
        cv2.imwrite( filename, frame)
        print('Image captured and saved as "captured_image.png"')       
    else:
        print("Failed to capture image.")
    cam.release()
    return FileResponse(path=filename, media_type='image/png', filename=filename)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=2077)