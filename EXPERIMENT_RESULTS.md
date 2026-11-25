# EcoSort — Comprehensive Experiment Results & Ablation Analysis

**Project Title:** EcoSort — AI-Powered Campus Waste Management System  
**Experiment Series:** EXP-2026-PHASE2  
**Evaluation Standard:** Independent, Stratified Real-World Test Partition ($N=141$)  
**Date:** November 25, 2026  
**Git Branch:** `phase-2-ml-improvement`  

---

## 1. Experimental Overview

To establish an academically rigorous baseline for the M.Sc. Computer Science dissertation, three model configurations were tested and benchmarked on the exact same dataset partition:

1. **Model A (Baseline V1):** The original MobileNetV2 checkpoint trained on 24 images with mixed synthetic data and inconsistent $[-1.0, 1.0]$ vs $[0.0, 1.0]$ preprocessing.
2. **Model B (Stage 1 Transfer Learning):** MobileNetV2 with frozen backbone trained on 646 real-world images using Adam ($\text{LR}=10^{-3}$) for 10 epochs.
3. **Model C (Stage 2 Fine-Tuned V2 - Production):** MobileNetV2 with top layers (from layer 110 onwards) unfrozen and fine-tuned using Adam ($\text{LR}=10^{-4}$) with ReduceLROnPlateau and EarlyStopping.

---

## 2. Quantitative Results & Comparison Matrix

| Metric | Model A (Baseline V1) | Model B (Stage 1 Frozen) | Model C (Stage 2 Fine-Tuned) | Absolute Gain (C vs A) |
| :--- | :---: | :---: | :---: | :---: |
| **Training Set Size** | 24 images | 646 images | 646 images | $+622$ images |
| **Test Accuracy** | 36.88% | 83.69% | **87.94%** | **+51.06%** |
| **Macro Precision** | 31.96% | 84.12% | **88.50%** | **+56.54%** |
| **Macro Recall** | 36.86% | 83.51% | **87.75%** | **+50.89%** |
| **Macro F1-Score** | 32.20% | 83.45% | **87.76%** | **+55.56%** |
| **Weighted F1-Score** | 32.20% | 83.58% | **87.88%** | **+55.68%** |
| **Mean Inference Latency** | 240 ms (Keras) | 240 ms (Keras) | **14 ms (LiteRT)** | **$17\times$ speedup** |
| **Model Binary Size** | 11.5 MB | 11.5 MB | **2.55 MB** | **$77.8\%$ reduction** |

---

## 3. Training & Convergence Dynamics

The two-stage training curves demonstrate healthy convergence without catastrophic forgetting:

- **Stage 1 (Epochs 1–10):**
  - Rapid convergence of the classification head.
  - Training accuracy climbed from 66.72% to 96.44%.
  - Validation accuracy stabilized around 86.86% with validation loss at 0.4611.
- **Stage 2 (Epochs 11–20):**
  - Fine-tuning the top convolutional blocks adjusted high-level receptive fields for textured waste materials.
  - Training accuracy reached 97.99% (loss: 0.0754).
  - Regularization (Dropout 0.30, BatchNormalization, ReduceLROnPlateau) prevented runaway overfitting.

*(Visual curves preserved at `reports/training_curves.png` and numerical history saved at `reports/training_history.json`)*.

---

## 4. Visual Artifacts Generated

The following empirical artifacts were generated and stored in `reports/`:
1. `reports/confusion_matrix.png`: High-resolution heatmap of the 6-class confusion matrix on the 141-sample test set.
2. `reports/training_curves.png`: Side-by-side plots of training/validation accuracy and training/validation categorical crossentropy loss across all 20 epochs.
3. `reports/sample_gradcam.png`: Verified sample of Grad-CAM saliency activation overlaid on test waste imagery.
4. `reports/evaluation_report.json`: Full machine-readable record of test metrics, confusion matrix arrays, and calibration threshold analysis.
5. `reports/training_history.json`: Epoch-by-epoch loss and accuracy metrics.

---

## 5. Known Limitations & Research Avenues

1. **Specular Reflection Challenge:** Specular highlights on curved clear plastics occasionally trigger false positive metal classifications. Polarized lenses or specular-invariant augmentations represent promising future improvements.
2. **Serverless Grad-CAM:** While full TensorFlow environments compute Grad-CAM heatmaps in real-time (~80 ms), serverless environments running lightweight LiteRT runtime cannot compute symbolic backward gradients. EcoSort cleanly handles this by serving ultra-fast predictions via LiteRT while offering Grad-CAM in full server environments.
3. **Compound Waste:** Complex multi-component waste (e.g., electronic items embedded in plastic packaging) presents inherent multi-label ambiguity that can be explored in future multi-label detection extensions.
