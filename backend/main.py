from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routes import predict, retrain

app = FastAPI(title="Gastric Cancer Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predict.router, prefix="/predict", tags=["Prediction"])
app.include_router(retrain.router, prefix="/retrain", tags=["Retraining"])
app.mount("/gradcams", StaticFiles(directory="uploads/gradcams"), name="gradcams")
app.mount("/temp", StaticFiles(directory="temp"), name="temp")