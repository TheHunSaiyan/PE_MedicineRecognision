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


COPY . .

RUN mkdir -p /app/Data/CapturedImages /app/Data/CalibrationImages /app/Data/UndistortedImages

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "2076"]