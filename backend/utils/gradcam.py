import tensorflow as tf
import numpy as np
import cv2
import os

def generate_gradcam(model, img_tensor, image_path, layer_name=None):
    if layer_name is None:
        for layer in reversed(model.layers):
            if isinstance(layer, tf.keras.layers.Conv2D):
                layer_name = layer.name
                break
        if layer_name is None:
            raise ValueError("No Conv2D layer found in the model.")

    grad_model = tf.keras.models.Model(
        [model.inputs], [model.get_layer(layer_name).output, model.output]
    )

    with tf.GradientTape() as tape:
        conv_outputs, predictions = grad_model(img_tensor)
        loss = predictions[:, 0]

    grads = tape.gradient(loss, conv_outputs)

    # Average over the spatial dimensions
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

    # Multiply each channel by "how important it is" with broadcasting
    conv_outputs = conv_outputs[0]  # shape: (H, W, C)
    heatmap = conv_outputs @ pooled_grads[..., tf.newaxis]  # shape: (H, W, 1)
    heatmap = tf.squeeze(heatmap)  # shape: (H, W)

    # Normalize heatmap
    heatmap = np.maximum(heatmap, 0) / (np.max(heatmap) + 1e-8)
    heatmap = cv2.resize(np.uint8(255 * heatmap), (224, 224))
    heatmap_color = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)

    # Superimpose on original image
    original_img = cv2.imread(image_path)
    original_img = cv2.resize(original_img, (224, 224))
    superimposed_img = cv2.addWeighted(original_img, 0.6, heatmap_color, 0.4, 0)

    os.makedirs("gradcams", exist_ok=True)
    gradcam_path = os.path.join("gradcams", os.path.basename(image_path))
    cv2.imwrite(gradcam_path, superimposed_img)

    return gradcam_path
