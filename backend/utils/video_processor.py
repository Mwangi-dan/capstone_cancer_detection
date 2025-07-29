import cv2
import os
from utils.preprocessing import preprocess_image
from utils.prediction import predict_image
from models.model_loader import load_model_once


def process_video(video_path, frame_skip=30):
    os.makedirs("temp", exist_ok=True) 
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
                "confidence": float(confidence),
                "image_path": f"/temp/frame_{frame_index}.jpg"
            })

            frame_index += 1

        frame_count += 1

    cap.release()
    return predictions
