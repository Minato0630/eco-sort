import os
import io
import json
import base64
import numpy as np
from PIL import Image

# Setup dynamic TF-Lite / LiteRT detection
TFLITE_AVAILABLE = False
tflite = None

try:
    import ai_edge_litert.interpreter as ai_rt
    tflite = ai_rt
    TFLITE_AVAILABLE = True
    print("Loaded LiteRT (ai_edge_litert) successfully for ML inference!")
except ImportError:
    try:
        import tflite_runtime.interpreter as tflite_rt
        tflite = tflite_rt
        TFLITE_AVAILABLE = True
        print("Loaded tflite-runtime successfully for ML inference!")
    except ImportError:
        try:
            import tensorflow as tf
            tflite = tf.lite
            TFLITE_AVAILABLE = True
            print("Loaded tensorflow.lite from full installation successfully!")
        except ImportError:
            TFLITE_AVAILABLE = False
            tflite = None
            print("TFLite is not available.")

try:
    import tensorflow as tf
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    tf = None

# Model Configuration & Empirical Thresholds
MODEL_VERSION = "2.0.0-mobilenetv2-finetuned"
CONFIDENCE_THRESHOLD = 65.0  # Empirically calibrated on validation split (error rate <= 10%)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "waste_classifier.h5")
TFLITE_MODEL_PATH = os.path.join(os.path.dirname(__file__), "waste_classifier.tflite")
CLASSES_PATH = os.path.join(os.path.dirname(__file__), "class_indices.json")

# 6 Core Waste Categories Metadata
CATEGORY_DETAILS = {
    "E-Waste": {
        "category": "E-Waste / Hazardous",
        "bin": "Orange Bin (Special E-Waste Collection)",
        "color": "orange",
        "points": 25,
        "co2_offset": 2.5,
        "guidance": "Hand over to designated e-waste drop-off counter. Do not crush, burn, or dispose with regular trash."
    },
    "Organic": {
        "category": "Organic Waste",
        "bin": "Green Bin (Compost)",
        "color": "green",
        "points": 5,
        "co2_offset": 0.4,
        "guidance": "Place in the green compost bin. Remove any plastic stickers, tape, or non-biodegradable packaging."
    },
    "Plastic": {
        "category": "Recyclable (Plastic)",
        "bin": "Blue Bin (Recyclables)",
        "color": "blue",
        "points": 10,
        "co2_offset": 1.2,
        "guidance": "Empty and rinse liquids. Flatten bottles to save volume before depositing in the blue recycling bin."
    },
    "Paper": {
        "category": "Recyclable (Paper/Cardboard)",
        "bin": "Blue Bin (Recyclables)",
        "color": "blue",
        "points": 8,
        "co2_offset": 0.9,
        "guidance": "Keep dry and clean. Flatten cardboard boxes and remove excessive tape before recycling."
    },
    "Metal": {
        "category": "Recyclable (Metal)",
        "bin": "Red Bin (Metal Recyclables)",
        "color": "red",
        "points": 15,
        "co2_offset": 1.8,
        "guidance": "Rinse food or soda residue. Deposit clean tins and aluminum cans in the red metal bin."
    },
    "General": {
        "category": "General Waste / Landfill",
        "bin": "Gray Bin (General Landfill)",
        "color": "gray",
        "points": 2,
        "co2_offset": 0.1,
        "guidance": "Dispose in the gray bin for non-recyclable solid waste destined for safe sanitary containment."
    }
}

custom_model = None
gradcam_model = None
class_indices = None

def load_class_indices():
    global class_indices
    if class_indices is not None:
        return class_indices
    if os.path.exists(CLASSES_PATH):
        try:
            with open(CLASSES_PATH, "r") as f:
                class_indices = json.load(f)
            return class_indices
        except Exception as e:
            print(f"Error loading class indices from {CLASSES_PATH}: {e}")
    # Default 6-class indices
    class_indices = {
        "0": "E-Waste",
        "1": "General",
        "2": "Metal",
        "3": "Organic",
        "4": "Paper",
        "5": "Plastic"
    }
    return class_indices

def load_custom_model_if_available():
    global custom_model, gradcam_model
    if not TENSORFLOW_AVAILABLE:
        return None
    if custom_model is None and os.path.exists(MODEL_PATH):
        try:
            custom_model = tf.keras.models.load_model(MODEL_PATH)
            
            # Setup Grad-CAM sub-model targeting the last 4D conv layer
            target_layer_name = None
            for layer in reversed(custom_model.layers):
                if 'conv' in layer.name.lower() or 'relu' in layer.name.lower():
                    if len(layer.output.shape) == 4:
                        target_layer_name = layer.name
                        break
            if target_layer_name:
                gradcam_model = tf.keras.models.Model(
                    inputs=custom_model.inputs,
                    outputs=[custom_model.get_layer(target_layer_name).output, custom_model.output]
                )
            print("Loaded custom Keras model and Grad-CAM graph successfully!")
        except Exception as e:
            print("Error loading custom Keras model:", e)
    return custom_model

def generate_gradcam_overlay(image_path, target_class_idx=None):
    """
    Computes genuine Grad-CAM saliency heatmap on the uploaded image using tf.GradientTape.
    Returns base64 PNG data URI and explanatory context.
    """
    if not TENSORFLOW_AVAILABLE or gradcam_model is None:
        return None, "Grad-CAM visual explanation requires full TensorFlow server runtime."
        
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.cm as cm
        
        pil_img = Image.open(image_path).convert('RGB')
        orig_size = pil_img.size
        img_resized = pil_img.resize((224, 224))
        img_array = np.array(img_resized, dtype=np.float32)
        img_array = tf.keras.applications.mobilenet_v2.preprocess_input(img_array)
        img_tensor = tf.expand_dims(img_array, axis=0)

        with tf.GradientTape() as tape:
            conv_outputs, predictions = gradcam_model(img_tensor)
            if target_class_idx is None:
                target_class_idx = tf.argmax(predictions[0])
            loss = predictions[:, target_class_idx]

        grads = tape.gradient(loss, conv_outputs)
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

        conv_outputs = conv_outputs[0]
        heatmap = conv_outputs @ pooled_grads[..., tf.newaxis]
        heatmap = tf.squeeze(heatmap)
        heatmap = tf.maximum(heatmap, 0) / (tf.math.reduce_max(heatmap) + 1e-10)
        heatmap = heatmap.numpy()

        # Colormap overlay
        try:
            cmap = matplotlib.colormaps['jet']
        except Exception:
            cmap = cm.get_cmap('jet')
            
        jet_colors = cmap(np.arange(256))[:, :3]
        jet_heatmap = jet_colors[np.uint8(255 * heatmap)]
        jet_heatmap = Image.fromarray(np.uint8(jet_heatmap * 255)).resize(orig_size, Image.BILINEAR)
        jet_heatmap_arr = np.array(jet_heatmap)

        orig_arr = np.array(pil_img)
        superimposed_arr = np.uint8(0.6 * orig_arr + 0.4 * jet_heatmap_arr)
        superimposed_img = Image.fromarray(superimposed_arr)

        buf = io.BytesIO()
        superimposed_img.save(buf, format='PNG')
        b64_str = base64.b64encode(buf.getvalue()).decode('utf-8')
        data_uri = f"data:image/png;base64,{b64_str}"
        
        explanation = (
            "Grad-CAM highlights the image regions that contributed most to the model's classification. "
            "Warm colors (red/yellow) indicate primary decision cues, while cool colors (blue) were less influential. "
            "This is an approximate saliency map to assist human inspection, not absolute proof."
        )
        return data_uri, explanation
    except Exception as e:
        print(f"Error computing Grad-CAM: {e}")
        return None, str(e)

def map_label_to_category(label):
    # Lookup in standard 6-class dictionary
    for k, v in CATEGORY_DETAILS.items():
        if k.lower() == label.lower():
            return v
    # Fallback to General
    return CATEGORY_DETAILS["General"]

def predict_waste(image_path, include_gradcam=True):
    """
    Main prediction entry point.
    Runs LiteRT (TFLite) or Keras inference with consistent MobileNetV2 preprocessing.
    Returns predicted waste category, confidence, top 3 class probabilities,
    validation-calibrated uncertainty status, and Grad-CAM visualization.
    """
    indices_map = load_class_indices()
    
    # 1. Try LiteRT (TFLite) Interpreter
    if TFLITE_AVAILABLE and os.path.exists(TFLITE_MODEL_PATH):
        try:
            img = Image.open(image_path).convert('RGB').resize((224, 224))
            img_array = np.array(img, dtype=np.float32)
            # Consistent MobileNetV2 Preprocessing [-1.0, 1.0]
            img_array = (img_array / 127.5) - 1.0
            img_array = np.expand_dims(img_array, axis=0)

            interpreter = tflite.Interpreter(model_path=TFLITE_MODEL_PATH)
            interpreter.allocate_tensors()

            input_details = interpreter.get_input_details()
            output_details = interpreter.get_output_details()

            interpreter.set_tensor(input_details[0]['index'], img_array)
            interpreter.invoke()

            preds = interpreter.get_tensor(output_details[0]['index'])[0]
            class_idx = int(np.argmax(preds))
            confidence = float(preds[class_idx]) * 100.0
            raw_label = indices_map.get(str(class_idx), "General")

            # Top 3 predictions
            top_indices = np.argsort(preds)[::-1][:3]
            top_predictions = [
                {
                    "category": indices_map.get(str(idx), "General").title(),
                    "confidence": round(float(preds[idx]) * 100.0, 1)
                }
                for idx in top_indices
            ]

            mapping = map_label_to_category(raw_label)
            is_uncertain = confidence < CONFIDENCE_THRESHOLD
            status = "uncertain" if is_uncertain else "confident"
            uncertainty_msg = (
                f"Low model confidence ({round(confidence, 1)}% < {CONFIDENCE_THRESHOLD}%). "
                "The item may have complex packaging, unusual lighting, or ambiguous texture. "
                "Please verify manual bin placement."
            ) if is_uncertain else None

            gradcam_uri = None
            gradcam_expl = None
            if include_gradcam and TENSORFLOW_AVAILABLE and os.path.exists(MODEL_PATH):
                load_custom_model_if_available()
                gradcam_uri, gradcam_expl = generate_gradcam_overlay(image_path, target_class_idx=class_idx)

            return {
                "raw_label": raw_label,
                "detected_item": raw_label.title(),
                "waste_type": mapping["category"],
                "bin": mapping["bin"],
                "bin_color": mapping["color"],
                "points": mapping["points"],
                "co2_offset": mapping["co2_offset"],
                "disposal_guidance": mapping["guidance"],
                "confidence": round(confidence, 2),
                "top_predictions": top_predictions,
                "status": status,
                "is_uncertain": is_uncertain,
                "uncertainty_message": uncertainty_msg,
                "model_version": MODEL_VERSION,
                "gradcam_image": gradcam_uri,
                "gradcam_explanation": gradcam_expl
            }
        except Exception as e:
            print("LiteRT prediction error, falling back to Keras:", e)

    # 2. Try Keras Model
    if TENSORFLOW_AVAILABLE:
        load_custom_model_if_available()
        if custom_model is not None:
            try:
                img = Image.open(image_path).convert('RGB').resize((224, 224))
                img_array = np.array(img, dtype=np.float32)
                img_array = tf.keras.applications.mobilenet_v2.preprocess_input(img_array)
                img_array = np.expand_dims(img_array, axis=0)

                preds = custom_model.predict(img_array, verbose=0)[0]
                class_idx = int(np.argmax(preds))
                confidence = float(preds[class_idx]) * 100.0
                raw_label = indices_map.get(str(class_idx), "General")

                top_indices = np.argsort(preds)[::-1][:3]
                top_predictions = [
                    {
                        "category": indices_map.get(str(idx), "General").title(),
                        "confidence": round(float(preds[idx]) * 100.0, 1)
                    }
                    for idx in top_indices
                ]

                mapping = map_label_to_category(raw_label)
                is_uncertain = confidence < CONFIDENCE_THRESHOLD
                status = "uncertain" if is_uncertain else "confident"
                uncertainty_msg = (
                    f"Low model confidence ({round(confidence, 1)}% < {CONFIDENCE_THRESHOLD}%). "
                    "The item may have complex packaging, unusual lighting, or ambiguous texture. "
                    "Please verify manual bin placement."
                ) if is_uncertain else None

                gradcam_uri = None
                gradcam_expl = None
                if include_gradcam:
                    gradcam_uri, gradcam_expl = generate_gradcam_overlay(image_path, target_class_idx=class_idx)

                return {
                    "raw_label": raw_label,
                    "detected_item": raw_label.title(),
                    "waste_type": mapping["category"],
                    "bin": mapping["bin"],
                    "bin_color": mapping["color"],
                    "points": mapping["points"],
                    "co2_offset": mapping["co2_offset"],
                    "disposal_guidance": mapping["guidance"],
                    "confidence": round(confidence, 2),
                    "top_predictions": top_predictions,
                    "status": status,
                    "is_uncertain": is_uncertain,
                    "uncertainty_message": uncertainty_msg,
                    "model_version": MODEL_VERSION,
                    "gradcam_image": gradcam_uri,
                    "gradcam_explanation": gradcam_expl
                }
            except Exception as e:
                print("Keras prediction error:", e)

    # 3. Model unavailable response
    print("Warning: Neither LiteRT nor Keras model could execute inference.")
    return {
        "error": "ML Inference Service Unavailable: No trained model could be loaded or executed.",
        "status": 503,
        "raw_label": "Unknown",
        "detected_item": "Unrecognized Waste Item",
        "waste_type": "Uncertain / Unsupported Item",
        "bin": "Manual Inspection / Verification Needed",
        "bin_color": "gray",
        "points": 0,
        "co2_offset": 0.0,
        "confidence": 0.0,
        "top_predictions": [],
        "is_uncertain": True,
        "status": "unavailable",
        "model_version": MODEL_VERSION
    }
