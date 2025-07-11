from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes import predict, retrain

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