# EcoSort — Empirical Model Evaluation & Comparative Performance Report

**Project Title:** EcoSort — AI-Based Campus Waste Management System  
**Document Type:** Empirical Model Evaluation & Baseline Comparison  
**Model Under Test:** EcoSort MobileNetV2 V2 (`2.0.0-mobilenetv2-finetuned`)  
**Baseline Model:** EcoSort MobileNetV2 V1 (`waste_classifier_v1.h5`)  
**Evaluation Partition:** 141 Untouched Real-World Test Images (`dataset_curated/test/`)  
**Evaluation Date:** November 25, 2026  
**Git Branch:** `phase-2-ml-improvement`  

---

## 1. Executive Summary

This report presents an empirical evaluation of the improved EcoSort V2 waste classification model against the previous V1 baseline. Both models were evaluated on the **exact same untouched real-world test partition** ($N=141$ images across all 6 classes).

### Key Performance Summary

| Metric | Baseline Model (V1) | Improved Model (V2) | Relative Improvement |
| :--- | :---: | :---: | :---: |
| **Overall Accuracy** | 36.88% | **87.94%** | **+51.06%** |
| **Macro Precision** | 31.96% | **88.50%** | **+56.54%** |
| **Macro Recall** | 36.86% | **87.75%** | **+50.89%** |
| **Macro F1-Score** | 32.20% | **87.76%** | **+55.56%** |
| **Weighted F1-Score** | 32.20% | **87.88%** | **+55.68%** |
| **Model Size** | 11.5 MB | **2.55 MB (LiteRT)** | **77.8% size reduction** |

---

## 2. Per-Class Performance Breakdown (Improved Model V2)

The improved model demonstrates high classification capability across all six categories, with near-perfect discriminative power on hazardous and organic waste streams:

| Waste Stream | Support ($N$) | Precision | Recall | F1-Score | Typical Misclassifications & Analysis |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **E-Waste** | 23 | **100.0%** | **100.0%** | **100.0%** | Flawless separation. Electronic circuitry and device geometries are highly distinct. |
| **Organic** | 24 | **100.0%** | **100.0%** | **100.0%** | Flawless separation. Textures of fruit peels and food waste are well learned. |
| **Paper** | 24 | **95.2%** | **83.3%** | **88.9%** | 4 instances misclassified as General or Metal due to reflective coated paper surfaces. |
| **Metal** | 24 | **74.2%** | **95.8%** | **83.6%** | Excellent recall (95.8%). Occasional false positives from shiny plastic or composite wrappers. |
| **Plastic** | 24 | **82.6%** | **79.2%** | **80.9%** | 5 instances confused with Metal due to shiny reflections on plastic bottles. |
| **General** | 22 | **78.9%** | **68.2%** | **73.2%** | Diverse composite items; some overlap with flexible plastics and crumpled paper. |
| **Macro Average** | **141** | **88.5%** | **87.8%** | **87.8%** | Balanced performance across all six classes without minority class degradation. |

---

## 3. Confusion Matrix Analysis

The confusion matrix on the 141 untouched test samples reveals the exact inter-class dynamics:

```
                  Predicted Class
                E-Waste General  Metal  Organic  Paper  Plastic
True Class:
E-Waste    [     23       0       0       0       0       0    ]
General    [      0      15       2       0       1       4    ]
Metal      [      0       1      23       0       0       0    ]
Organic    [      0       0       0      24       0       0    ]
Paper      [      0       3       1       0      20       0    ]
Plastic    [      0       0       5       0       0      19    ]
```

### Key Analytical Takeaways
1. **Zero Contamination in Hazardous / Organic Streams:** Zero non-organic items were routed to the green compost bin, and zero hazardous e-waste items were classified as general landfill trash.
2. **Plastic vs. Metal Reflection Ambiguity:** 5 transparent or reflective plastic bottles were predicted as metal due to high specular highlights on curved surfaces. This is a common computer vision challenge that is mitigated by EcoSort's top-3 alternative predictions.
3. **General / Composite Packaging Ambiguity:** 4 general waste items (snack bags with metallized film) were distributed between plastic and metal.

---

## 4. Uncertainty & Out-of-Distribution Calibration

Rather than employing an arbitrary confidence threshold, the cutoff was empirically calibrated across the 137-image validation set by measuring prediction error rates across confidence bins:

| Threshold ($\tau$) | Validation Coverage | Accuracy Above Threshold | Error Rate Above Threshold |
| :---: | :---: | :---: | :---: |
| 50.0% | 94.2% | 89.1% | 10.9% |
| 60.0% | 89.8% | 91.1% | 8.9% |
| **65.0% (Selected)** | **86.1%** | **93.2%** | **6.8%** |
| 70.0% | 82.5% | 94.7% | 5.3% |
| 80.0% | 75.9% | 97.1% | 2.9% |

### Policy Decision
A **65% confidence threshold** was chosen. This preserves **86.1% automatic sorting coverage** while reducing the sorting error rate to **6.8%**. Images below 65% trigger an uncertainty warning banner prompting the student or collector to visually inspect the item.

---

## 5. Grad-CAM Visual Saliency Evaluation

To provide interpretability for academic defense, Grad-CAM (Gradient-weighted Class Activation Mapping) was implemented targeting the final convolutional layer (`out_relu`) of MobileNetV2:

1. **Salient Focus:** Heatmaps demonstrate that the model consistently focuses on discriminative object features (e.g., keyboard key grids, bottle caps, can pull-tabs, and banana peel stems) rather than background posterboard or desk textures.
2. **Transparent Disclosure:** The frontend UI includes an explicit academic disclaimer explaining that Grad-CAM produces an approximate visual explanation of neural network activation, serving as a human-assistive tool rather than proof of correctness.
