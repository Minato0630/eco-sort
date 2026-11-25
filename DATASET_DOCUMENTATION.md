# EcoSort — Dataset Engineering & Data Integrity Documentation

**Document Title:** EcoSort Machine Learning Dataset Specification  
**Project:** EcoSort — AI-Based Campus Waste Management System  
**Academic Level:** M.Sc. Computer Science Final Year Dissertation  
**Version:** 2.0.0 (Curated & Expanded)  
**Date:** November 25, 2026  
**Repository:** `Minato0630/eco-sort`  
**Branch:** `phase-2-ml-improvement`  

---

## 1. Dataset Overview & Motivation

In Phase 0 and the initial audit of EcoSort, the training dataset was identified as critically undersized:
- **Baseline Dataset:** Exactly 25 total image files across 6 classes (with 10 synthetic AI-generated images and 15 real-world photos).
- **Consequences:** The baseline model suffered from severe overfitting, catastrophic cross-class confusion on real waste items (baseline test accuracy: 36.88%), and input distribution mismatch.

In Phase 2, the dataset was systematically curated and expanded using verified open-access, permissively licensed research datasets to reach a robust **924 verified real-world images** with balanced class distributions, strict train/validation/test stratification, and zero data leakage.

---

## 2. Dataset Inventory & Class Distribution

The curated EcoSort V2 dataset comprises **924 high-resolution, verified real-world RGB images** categorized into the six standard campus waste streams. All images have been deduplicated using MD5 cryptographic checksums, converted to clean 3-channel RGB, and resized to $224 \times 224$ during pipeline feeding.

| Category | Real-World Images | Train (70%) | Validation (15%) | Test (15%, Untouched) | Primary Real-World Sources & Waste Types |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Organic** | **160** | 112 | 24 | 24 | Kaggle/HuggingFace Waste Classification (156), Original real samples (4): Banana peels, orange rinds, leftover food, vegetable scraps. |
| **Plastic** | **160** | 112 | 24 | 24 | Stanford TrashNet (157), Original real samples (3): PET water bottles, soft drink containers, plastic carry bags, food packaging. |
| **Paper** | **160** | 112 | 24 | 24 | Stanford TrashNet Paper & Cardboard (157), Original real samples (3): Flattened cartons, office paper, newspapers, exam sheets. |
| **Metal** | **160** | 112 | 24 | 24 | Stanford TrashNet (158), Original real samples (2): Aluminum beverage cans, food tins, metal caps, crushed soda cans. |
| **E-Waste** | **146** | 102 | 21 | 23 | EWasteNet IEEE 2023 (144), Original real samples (2): Keyboards, mice, mobile phones, printed circuit boards, cables, laptops. |
| **General** | **138** | 96 | 20 | 22 | Stanford TrashNet Trash (137), Original real samples (1): Multi-layer snack wrappers, broken ceramics, dirty non-recyclables. |
| **TOTAL** | **924** | **646** | **137** | **141** | **100% Real-World Verified Imagery** |

---

## 3. Data Provenance & Licensing

To ensure full compliance with academic ethics and open-source licenses, all acquired datasets originate from documented peer-reviewed research or open-database repositories:

1. **Stanford TrashNet (CS229 Research Project)**
   - **Authors:** Gary Thung & Mindy Yang, Stanford University.
   - **Publication:** *Classification of Trash for Recyclability Status*, CS229 Report, 2016.
   - **License:** Open Source (MIT License).
   - **Classes Utilized:** `plastic` (157), `paper` + `cardboard` (157), `metal` (158), `trash` (137).
   - **Capture Conditions:** iPhone cameras (7 Plus, 5S, SE) against white posterboard backgrounds with natural sunlight and interior room illumination.

2. **EWasteNet (E-Waste Vision Dataset)**
   - **Authors:** Md. Niful Islam et al.
   - **Publication:** *EWasteNet: A Two-Stream DeiT Approach for E-Waste Classification*, IEEE 8th International Conference on Software Engineering & Computer Systems (ICSECS 2023).
   - **License:** Academic Open Access / CC BY 4.0.
   - **Classes Utilized:** Real-world consumer electronic waste across 6 hardware subcategories: Keyboards, mice, mobile devices, cameras, laptops, and smartwatches.

3. **Waste Classification Dataset (Organic Sub-split)**
   - **Authors:** Sashaank Sekar et al.
   - **Host:** Kaggle & Hugging Face (`bryandts/waste_organic_anorganic_classification`).
   - **License:** Open Database License (ODbL) / MIT.
   - **Classes Utilized:** Organic food waste, fruit peels, decaying organic matter, cafeteria kitchen scraps.

4. **Original EcoSort Campus Photographs**
   - **Origin:** Bishop Heber College campus collection (real photos: `banana peel.jpg`, `apple_core.jpg`, `soda_can.jpg`, `mobile wate.jpg`, etc.).
   - **License:** University Project Proprietary / Open Academic.

---

## 4. Synthetic vs. Real-World Image Isolation

In the initial repository audit, 10 synthetic AI-generated images were identified in `dataset/` (e.g., `rotting_orange.jpg`, `broken_tv_remote.jpg`, `crushed_soda_can.jpg`).
- **Isolation Policy:** All synthetic images were **strictly excluded** from the final test set (`dataset_curated/test/`).
- **Evaluation Integrity:** The test set of 141 images contains **exclusively real photographs** taken in physical settings to guarantee that model generalization benchmarks represent genuine real-world waste detection.

---

## 5. Splitting Protocol & Leakage Prevention

- **Split Ratio:** 70% Training ($N=646$), 15% Validation ($N=137$), 15% Testing ($N=141$).
- **Stratification:** Splitting was performed within each class independently using a fixed random seed (`seed=42`) to guarantee identical class representation across all three partitions.
- **Deduplication:** Perceptual file checks and MD5 hashing were applied prior to splitting. No duplicate file or identical crop exists across training and test sets.
- **Untouched Test Set:** The test set was physically placed in `dataset_curated/test/` and was never exposed to training, data augmentation, hyperparameter tuning, or early-stopping decisions.
