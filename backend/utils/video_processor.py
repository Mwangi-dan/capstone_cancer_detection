import cv2
import os
from backend.utils.preprocessing import preprocess_image
from backend.utils.prediction import predict_image
from backend.models.model_loader import load_model_once

def process_video(video_path, frame_skip=30):
    cap = cv2.VideoCapture(video_path)
    model = load_model_once()
    predictions = []

    frame_count = 0
    frame_index = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frame_skip == 0:
            frame_path = f"temp/frame_{frame_index}.jpg"
            cv2.imwrite(frame_path, frame)
            img_tensor = preprocess_image(frame_path)
            label, confidence = predict_image(model, img_tensor)

            predictions.append({
                "frame": frame_index,
                "label": label,
                "confidence": float(confidence)
            })

            frame_index += 1

        frame_count += 1

    cap.release()
    return predictions
