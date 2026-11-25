# EcoSort — Deep Learning Model Training & Transfer Learning Report

**Project Title:** EcoSort — AI-Powered Campus Waste Classification  
**Target Architecture:** MobileNetV2 with Transfer Learning & Progressive Fine-Tuning  
**Document Type:** Model Training Specification & Experimental Log  
**Model Version:** `2.0.0-mobilenetv2-finetuned`  
**Training Date:** November 25, 2026  
**Git Branch:** `phase-2-ml-improvement`  

---

## 1. Executive Summary

This report documents the architectural design, preprocessing pipeline, two-stage transfer learning procedure, and regularization strategy used to train the production EcoSort waste classification model.

By leveraging an ImageNet-pretrained **MobileNetV2** backbone coupled with a custom dense classification head and progressive fine-tuning of top convolutional blocks, the model achieved:
- **Final Training Accuracy:** 97.99% (Loss: 0.0754)
- **Validation Accuracy:** 86.86% (Loss: 0.5527)
- **Exported LiteRT Footprint:** **2.55 MB** (optimized for low-latency serverless edge inference)

---

## 2. Preprocessing & Data Pipeline Specification

A critical defect identified in the initial audit was **preprocessing distribution mismatch**: the training script used $[0.0, 1.0]$ normalization while the inference engine applied $[-1.0, 1.0]$. In Phase 2, a strictly unified preprocessing contract was established:

### 2.1 Input Standardization
- **Resolution:** $224 \times 224 \times 3$ (RGB)
- **Normalization Equation:**
  $$\hat{x} = \frac{x}{127.5} - 1.0, \quad \hat{x} \in [-1.0, 1.0]$$
  *(Identical to `tf.keras.applications.mobilenet_v2.preprocess_input`)*

### 2.2 Data Augmentation (Training Partition Only)
To prevent overfitting while preserving natural waste geometries, data augmentation was applied **exclusively to the training partition** ($N=646$):
- Random Rotation: $\pm 25^\circ$
- Width & Height Shifts: $\pm 15\%$
- Shear Range: $15\%$
- Zoom Range: $\pm 15\%$
- Horizontal Flip: Enabled (50% probability)
- Fill Mode: Nearest

The validation ($N=137$) and test ($N=141$) partitions were evaluated in an unaugmented state to ensure that reported metrics reflect unmodified real-world image performance.

---

## 3. Neural Network Architecture

MobileNetV2 was selected due to its inverted residual structure, linear bottlenecks, depthwise separable convolutions, and optimal balance of representational power and computational efficiency for mobile and serverless deployments.

```
Input Image (224 x 224 x 3)
      │
MobileNetV2 Pretrained Backbone (155 layers, ImageNet weights)
      │
Conv Layer 'out_relu' (7 x 7 x 1280) ──> [Grad-CAM Extraction Point]
      │
GlobalAveragePooling2D
      │
BatchNormalization
      │
Dense (128 units, ReLU activation, He Normal initialization)
      │
Dropout (rate = 0.30)
      │
Dense (6 units, Softmax activation) ──> [Class Probabilities]
```

### Parameter Breakdown
- **Base Backbone Parameters:** 2,257,984
- **Classification Head Parameters:** 164,870
- **Total Parameters:** 2,422,854
- **Trainable Parameters (Stage 1):** 164,614
- **Trainable Parameters (Stage 2):** 1,223,814

---

## 4. Two-Stage Training Protocol

Training was executed in two distinct, sequential stages using the Adam optimizer and Categorical Crossentropy loss:

### Stage 1: Feature Extraction (Frozen Trunk)
- **Epochs:** 10
- **Frozen Layers:** Layers 0 through 154 of MobileNetV2 (100% frozen).
- **Learning Rate:** $1.0 \times 10^{-3}$
- **Objective:** Train the newly initialized dense classification head without corrupting the pretrained feature representations.
- **Stage 1 Epoch 1:** Train Acc: 66.72%, Val Acc: 78.10%
- **Stage 1 Epoch 10:** Train Acc: 96.44%, Val Acc: 86.86% (Val Loss: 0.4611)

### Stage 2: Progressive Fine-Tuning
- **Epochs:** 10
- **Unfrozen Layers:** Layers 110 through 154 (top bottleneck blocks and pointwise $1 \times 1$ conv).
- **Learning Rate:** $1.0 \times 10^{-4}$ (reduced by $10\times$ to avoid destructive gradient updates).
- **Callbacks:**
  - `ModelCheckpoint`: Saved best checkpoint based on minimum validation loss (`val_loss`).
  - `EarlyStopping`: Monitored `val_loss` with patience of 4 epochs and automatic weight restoration.
  - `ReduceLROnPlateau`: Halved learning rate when validation loss plateaued for 2 epochs (min LR: $1 \times 10^{-6}$).
- **Stage 2 Epoch 10:** Train Acc: 97.99%, Val Acc: 86.86% (Val Loss: 0.5527)

---

## 5. Model Export & Edge Optimization

The optimal model checkpoint was exported into two distribution formats:

1. **Keras Format (`backend/waste_classifier.h5`):**
   - Size: 11.2 MB
   - Used in server environments with full TensorFlow support for computing symbolic gradients and Grad-CAM saliency maps.
2. **LiteRT / TFLite FlatBuffer (`backend/waste_classifier.tflite`):**
   - Size: **2.55 MB** (via standard TFLite converter with default quantization optimizations).
   - Used for production edge and serverless deployment on Vercel (`api/index.py`), reducing serverless memory overhead and eliminating heavy Python package dependencies.
