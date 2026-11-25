# EcoSort — Known Limitations & Research Avenues

**Project Title:** EcoSort — AI-Powered Campus Waste Management System  
**Academic Document Classification:** Technical Limitations & Future Work  
**Date:** November 25, 2026  
**Git Branch:** `phase-3-system-integration`  

---

## 1. Computer Vision & Environmental Limitations

### 1.1 Specular Highlights on Curved Transparent Plastics
- **Observation:** In the empirical confusion matrix on the 141-sample test set, 5 out of 24 plastic samples (primarily transparent PET bottles under direct artificial lighting) were classified as Metal.
- **Root Cause:** Curved transparent plastics create sharp specular glare lines that closely mimic the reflective sheen of aluminum cans and tin foil.
- **Mitigation in EcoSort:** Mitigated by displaying the ranked top-3 probability distribution and a calibrated uncertainty alert banner when confidence is below 65%.
- **Future Research Direction:** Polarizing lens filters or specular-invariant contrastive augmentation during training.

### 1.2 Compound & Multi-Material Waste Items
- **Observation:** Real-world items such as electronic toys or lithium battery packs embedded inside molded plastic blister packaging contain multiple waste categories simultaneously.
- **Current Behavior:** MobileNetV2 performs single-label multi-class classification and assigns the dominant visual class.
- **Future Research Direction:** Multi-label object detection (e.g., YOLOv8 / YOLOv10) to generate bounding boxes for individual components on a conveyor or sorting tray.

---

## 2. Infrastructure & Deployment Limitations

### 2.1 Serverless Grad-CAM Computation
- **Observation:** Grad-CAM saliency heatmaps require backward automatic differentiation (`tf.GradientTape`) across the final convolutional layer (`out_relu`).
- **Serverless Boundary:** Google's standalone `ai-edge-litert` (LiteRT) runtime is designed purely for forward inference and does not include backward automatic differentiation.
- **Current Behavior:** Full Grad-CAM heatmaps are generated when running in local/GPU Python server environments with TensorFlow installed. In serverless LiteRT environments (such as Vercel), the API safely falls back to LiteRT inference and returns `gradcam_image: null` with an explanatory message.
- **Future Solution:** Pre-computing or serving a dedicated Python GPU microservice for explainability overlays.

### 2.2 Serverless SQLite Storage Persistence
- **Observation:** Vercel functions execute in stateless, ephemeral microVM instances. Writing to SQLite on Vercel modifies the instance-local `/tmp/waste_sorting.db`, which does not persist across new deployments or warm instance reboots.
- **Recommendation:** Maintain SQLite for local testing, evaluation, and offline viva demonstrations; migrate production to a managed PostgreSQL cluster (Supabase / Neon) for permanent campus-wide adoption.

### 2.3 Simulated Background Model Retraining
- **Observation:** On serverless platforms, spawning background worker threads (`threading.Thread`) with subprocesses to execute `backend/train.py` is terminated as soon as the HTTP response terminates.
- **Current Behavior:** Retraining is supported in persistent local server mode (`python backend/app.py`). On serverless edge, retraining triggers should be offloaded to an asynchronous message queue (e.g., Celery / AWS SQS / GitHub Actions dispatch).
