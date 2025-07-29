# Gastric Cancer Detection System using Deep Learning

This project is a full-stack medical diagnostic system for the early detection of gastric cancer from endoscopic images using deep learning. The solution is designed to aid clinicians in identifying cancerous lesions through a web-based interface powered by a trained convolutional neural network (CNN) and explainable AI via Grad-CAM visualizations.

## Screenshots
PC
![Gastric Cancer Detection System](./images/gstroDetect_screenshot.png)

Mobile
![Gastric Cancer Detection System Mobile](./images/gstroDetect_mobile.png)

## Table of Contents
- [Live site](#live-site)
- [Link to video demo](#link-to-video-demo)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Model Training Summary](#model-training-summary)
- [Folder Structure](#folder-structure)
- [Installation](#installation)
- [Docker Setup](#docker-setup)
- [Testing the System](#testing-the-system)
- [Admin Features](#admin-features)
- [Author](#author)

## Live site

[Link to website](https://gastric-flask-app.azurewebsites.net/)

## Link to video demo
[Link to video demo](https://drive.google.com/file/d/1Nqz_d4LTL5yrCagBvI79xa8SGA5VdlHq/view?usp=sharing)

## Features

- Image Classification: Predicts whether an uploaded endoscopic image shows a cancerous or non-cancerous lesion.
- Deep Learning Model: Fine-tuned ResNet50 model using transfer learning and trained on the Kvasir and local datasets.
- Grad-CAM Visualization: Provides heatmaps to interpret model predictions by highlighting key areas of interest in the image.
- Authentication & Authorization:
  - Clinician-only access.
  - Admin verification for licensed medical professionals.
- User History & Logs: Stores past predictions, Grad-CAM results, and reports per user.
- Model Retraining Pipeline:
  - Upload new image data.
  - Trigger model retraining with user data to improve performance.
- Data Visualizations: Dashboard for metrics and visual summaries of predictions.
- Educational Tools: Includes a quiz game to teach users how to visually distinguish cancerous lesions.

## System Architecture

### Components

- Frontend: Flask (Jinja2 + Tailwind CSS)
- Backend: FastAPI for model inference and retraining
- Database: PostgreSQL via SQLAlchemy ORM
- Model: TensorFlow/Keras ResNet50 with Grad-CAM (OpenCV)
- Deployment: Dockerized containers

### Workflow

1. User uploads image via the web interface.
2. The image is sent to the FastAPI backend.
3. The backend:
   - Loads the trained model.
   - Runs prediction.
   - Generates a Grad-CAM image.
4. Results are returned to the frontend and displayed.
5. Verified users can:
   - View history.
   - Download results.
   - Submit images for retraining.
   - Configure profile settings.
6. Admin users can:
   - Verify new clinicians.
   - Manage user roles.
   - Monitor logs and metrics.

## Model Training Summary

| Parameter         | Value               |
|------------------|---------------------|
| Input Size       | 224x224             |
| Optimizer        | Adam                |
| Learning Rate    | 1e-5                |
| Epochs           | 20                  |
| Batch Size       | 32                  |
| Validation Split | 20%                 |
| Training Accuracy| 92.91%              |
| Validation Acc   | 91.87%              |
| Validation Loss  | 7.11                |

## Folder Structure

```
.
├── frontend/              # Flask UI
    ├── static/                # Tailwind CSS and images
    ├── templates/             # HTML templates
    ├── database/              
├── backend/               # FastAPI API
├── model/                 # Trained models & Grad-CAM logic
├──requirements.txt        # Contains packagesused for the project
├── Dockerfile             # Backend container
├── docker-compose.yml     # Multi-container setup
└── README.md              
```

## Installation

```bash
# Clone the repo
git clone https://github.com/yourusername/gastric-cancer-detection.git
cd gastric-cancer-detection

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
```

Set up the `.env` file with your database credentials and secret keys.

```env
DATABASE_URL=postgresql://user:password@localhost/dbname
SECRET_KEY=your-secret-key
MODEL_PATH=model/resnet50_kvasir_final_best.h5
```

## Docker Setup

```bash
# Build and run the containers
docker-compose up --build
```

## Testing the System

1. Launch the Flask frontend on http://localhost:5000
2. Register as a new clinician.
3. Upload an image on the prediction page.
4. Upload video for prediction.
5. View results with Grad-CAM.
6. Explore your history and reports after logging in.

## Admin Features

- Login as superadmin (manually seeded)
- Verify new clinician accounts
- Initiate retraining of model
- View activity logs and retraining status

## Author

Daniel Ndung'u 

Email: d.ndungu@alustudent.com

