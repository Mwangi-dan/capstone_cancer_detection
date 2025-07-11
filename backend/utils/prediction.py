import numpy as np

def predict_image(model, img_tensor):
    preds = model.predict(img_tensor)[0]
    label = int(preds[0] > 0.5)
    confidence = preds[0] if label == 1 else 1 - preds[0]
    return ("Non-Cancerous" if label == 1 else "Cancerous", confidence)
