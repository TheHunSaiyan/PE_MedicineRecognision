import os
import cv2
import numpy as np
from ultralytics import YOLO

model_path = "/home/thehunsaiyan/Desktop/PE_MedicineRecognision/Data/SegmentationWeights/best.pt"
model = YOLO(model_path, task='segment')

source = "/home/thehunsaiyan/Desktop/PE_MedicineRecognision/Data/Dataset/apranax_550_mg/images/train"

output_dir = "/home/thehunsaiyan/Desktop/qwsdg"
os.makedirs(output_dir, exist_ok=True)

image_files = [os.path.join(source, f) for f in os.listdir(source)
               if f.lower().endswith('.jpg')]
image_files = image_files[:10]

print(f"Processing {len(image_files)} images")

for i, image_path in enumerate(image_files):
    print(
        f"Processing image {i+1}/{len(image_files)}: {os.path.basename(image_path)}")

    try:
        results = model(image_path)

        for r in results:
            img = r.orig_img

            if r.masks is not None:
                masks = r.masks.data
                boxes = r.boxes

                for j, (mask, box) in enumerate(zip(masks, boxes)):
                    mask = mask.cpu().numpy()
                    mask = cv2.resize(mask, (img.shape[1], img.shape[0]))

                    binary_mask = (mask > 0.5).astype(np.uint8) * 255

                    background = np.full_like(img, (145, 145, 145))

                    extracted_pill = np.where(
                        binary_mask[..., None] == 255, img, background)

                    x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())

                    padding = 10
                    x1 = max(0, x1 - padding)
                    y1 = max(0, y1 - padding)
                    x2 = min(img.shape[1], x2 + padding)
                    y2 = min(img.shape[0], y2 + padding)

                    cropped_pill = extracted_pill[y1:y2, x1:x2]

                    output_path = os.path.join(
                        output_dir, f"image_{i}_pill_{j}.jpg")
                    cv2.imwrite(output_path, cropped_pill)

                    print(f"Saved: {output_path}")
            else:
                print(f"No masks found in image {i}")

    except Exception as e:
        print(f"Error processing {image_path}: {str(e)}")
        continue

print("Extraction complete!")
