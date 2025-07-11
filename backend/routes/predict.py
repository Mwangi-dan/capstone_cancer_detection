from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse
from backend.models.model_loader import load_model_once
from backend.utils.preprocessing import preprocess_image
from backend.utils.prediction import predict_image
from backend.utils.gradcam import generate_gradcam
from backend.utils.video_processor import process_video
import shutil
import os

router = APIRouter()
model = load_model_once()

@router.post("/")
async def predict(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        filepath = f"temp/{file.filename}"
        os.makedirs("temp", exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(contents)

        img_tensor = preprocess_image(filepath)
        label, confidence = predict_image(model, img_tensor)
        gradcam_path = generate_gradcam(model, img_tensor, filepath)

        return JSONResponse({
            "label": label,
            "confidence": float(confidence),
            "gradcam_path": gradcam_path
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


# Real-time (video) prediction endpoint
@router.post("/video")
async def predict_video(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        video_path = f"temp/{file.filename}"
        os.makedirs("temp", exist_ok=True)
        with open(video_path, "wb") as f:
            f.write(contents)

        # Extract frames and run predictions
        predictions = process_video(video_path)

        return JSONResponse({"frame_predictions": predictions})

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
