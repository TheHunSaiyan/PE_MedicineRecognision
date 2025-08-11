FROM python:3.13-slim

RUN apt-get update && \
    apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
RUN pip3 install python-multipart
RUN pip3 install pillow
RUN pip3 install qrcode pillow
RUN pip3 install pyserial
RUN pip3 install scikit-image
RUN pip3 install tqdm
RUN pip3 install ultralytics
RUN pip3 install passlib
RUN pip3 install bcrypt
RUN pip3 install python-jose[cryptography] passlib


COPY . .

RUN mkdir -p /app/Data/CapturedImages /app/Data/CalibrationImages /app/Data/UndistortedImages

RUN mkdir -p /app/.ultralytics && chmod 777 /app/.ultralytics
ENV YOLO_CONFIG_DIR=/app/.ultralytics

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "2076"]