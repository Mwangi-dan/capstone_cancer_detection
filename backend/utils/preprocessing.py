from tensorflow.keras.preprocessing.image import load_img, img_to_array
import numpy as np

def preprocess_image(path, target_size=(224, 224)):
    img = load_img(path, target_size=target_size)
    img = img_to_array(img)
    img = img / 255.0
    return np.expand_dims(img, axis=0)
