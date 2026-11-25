# Bishop Heber College — EcoSort (AI-Powered Campus Waste Management System)

[![Production Deployment](https://img.shields.io/badge/Vercel-Deployed-success?style=flat&logo=vercel)](https://bhc-ecosort.vercel.app/)
[![License: MIT](https://img.shields.io/badge/License-MIT-forestgreen.svg)](LICENSE)
[![Python: 3.10 | 3.12](https://img.shields.io/badge/Python-3.10%20%7C%203.12-blue.svg?logo=python)](https://www.python.org/)
[![Model: MobileNetV2](https://img.shields.io/badge/Model-MobileNetV2%20(LiteRT)-emerald.svg)](backend/waste_classifier.tflite)
[![Test Suite](https://img.shields.io/badge/Tests-21%2F21%20Passing-brightgreen.svg)](TESTING_REPORT.md)

**BHC EcoSort** is an enterprise-grade, AI-powered smart green portal and campus solid waste classification system designed for **Bishop Heber College (Autonomous)**, Tiruchirappalli. Developed as an individual final-semester research and engineering project for the **Master of Science in Computer Science (M.Sc. CS)** degree, the platform bridges deep computer vision with campus sustainability operations.

The platform provides automated waste stream segregation across six campus solid waste categories, explainable AI (Grad-CAM), uncertainty calibration, automated pickup logistics, gamified student reward points, department leaderboards, and an administrative control center.

---

## Quick Navigation

* 🌐 **Live Production Application:** [https://bhc-ecosort.vercel.app/](https://bhc-ecosort.vercel.app/)
* 📦 **GitHub Repository:** [https://github.com/Minato0630/eco-sort.git](https://github.com/Minato0630/eco-sort.git)
* 📖 **Academic Project Report (10 Chapters):** [docs/project-report/PROJECT_REPORT.md](file:///c:/Users/pandi/PROJECTS/waste-sorting-ml/docs/project-report/PROJECT_REPORT.md)
* 📊 **Empirical Model Evaluation:** [MODEL_EVALUATION_REPORT.md](file:///c:/Users/pandi/PROJECTS/waste-sorting-ml/MODEL_EVALUATION_REPORT.md)
* 🧪 **Automated Testing Suite (21/21 Passing):** [TESTING_REPORT.md](file:///c:/Users/pandi/PROJECTS/waste-sorting-ml/TESTING_REPORT.md)
* 🔌 **REST API Documentation:** [API_DOCUMENTATION.md](file:///c:/Users/pandi/PROJECTS/waste-sorting-ml/API_DOCUMENTATION.md)
* 🚀 **Vercel Serverless Architecture:** [DEPLOYMENT_REPORT.md](file:///c:/Users/pandi/PROJECTS/waste-sorting-ml/DEPLOYMENT_REPORT.md)

---

## 1. Key Features & Innovations

### 🧠 Advanced Deep Learning (MobileNetV2 & LiteRT)
* **High Empirical Accuracy:** Fine-tuned MobileNetV2 achieving **87.94% overall accuracy** and **87.76% macro F1-score** across 6 balanced waste streams, outperforming the initial baseline (+51.06% gain).
* **LiteRT Edge Inference:** Quantized and exported to Google LiteRT (`backend/waste_classifier.tflite`, **2.55 MB**, 77.8% size reduction), enabling sub-50ms inference on CPU and serverless lambdas.
* **Explainable AI (Grad-CAM):** Integrated Gradient-weighted Class Activation Mapping (`tf.GradientTape`) generating visual saliency heatmaps overlaid on uploaded images so users can understand which visual features triggered the classification.
* **Uncertainty Calibration:** Real-time softmax probability gating with an empirically calibrated threshold of **65.0%**. Low-confidence scans return secondary candidate predictions and prompt for manual confirmation.

### 🎨 Modern EcoSort V2 Design System
* **Environmental Technology Theme:** Forest Green (`#2d6a4f`), Emerald Green (`#52b788`), Charcoal, and Clean Slate palettes.
* **Functional Theme Engine:** Seamless Light and Dark mode switching persistent via `localStorage` with system-preference detection (`frontend/js/theme.js`).
* **Interactive Dashboards:** Tailored interfaces for Students, Campus Waste Collectors, and Administrative Staff with Leaflet.js campus maps and Chart.js telemetry.
* **Responsive Audio-Visual Feedback:** Real-time webcam scanning with laser animation, drag-and-drop file processing, and toast notifications.

### 🛡️ Enterprise Security & Data Integrity
* **Cryptographic Session Authentication:** Signed Bearer tokens via itsdangerous `URLSafeTimedSerializer` (`Authorization: Bearer <token>`).
* **Strict Role-Based Access Control (RBAC):** Hierarchical permissions across `Student`, `Collector`, `Admin`, and `SuperAdmin`.
* **Zero Trust & IDOR Protection:** Students can only view and modify their own scans and pickups; department admins are isolated to their specific academic departments.
* **Safe OTP Password Recovery:** 6-digit one-time password stored in-memory as salted SHA-256 hashes with 10-minute expiry; zero OTP exposure in API payloads.
* **Comprehensive Activity Telemetry:** Full audit trail logging in SQLite (`activity_logs`) capturing user IDs, timestamps, actions, and client IP addresses.

---

## 2. System Architecture

EcoSort implements a 3-tier decoupled architecture supporting both local server execution and serverless edge deployment on Vercel:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION TIER (CLIENT)                      │
│                                                                        │
│   Student Portal          Admin Governance          Collector Hub      │
│  (frontend/index.html)   (frontend/admin.html)  (frontend/collector.html│
│           │                       │                         │          │
│           └───────────────────────┴─────────────────────────┘          │
│                                   │                                    │
│                 EcoSort Design System & Theme Engine                   │
│               (frontend/css/ecosort.css, js/theme.js)                  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS / REST (JSON + Multipart)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        APPLICATION TIER (BACKEND)                      │
│                                                                        │
│                           Flask REST Server                            │
│                  (backend/app.py / api/index.py)                       │
│                                   │                                    │
│  ┌─────────────────┬──────────────┴───┬─────────────────┐              │
│  │ Auth & RBAC     │ Prediction       │ Pickup Dispatch │ Audit Logs   │
│  │ (itsdangerous)  │ Controller       │ Manager         │ Telemetry    │
│  └─────────────────┴──────────────┬───┴─────────────────┴──────────────┘
│                                   │
│                                   ▼
│                 Deep Learning Classification Engine                     │
│                       (backend/model.py)                               │
│                   ├── LiteRT Runtime (ai-edge-litert)                  │
│                   ├── MobileNetV2 (.tflite / .h5)                      │
│                   ├── Uncertainty Evaluator (Threshold = 65%)          │
│                   └── Grad-CAM Visual Explainability                   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ SQL (Row Factory / Parameterized)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          DATA PERSISTENCE TIER                         │
│                                                                        │
│                     Relational Database (SQLite3)                      │
│        Tables: users | waste_logs | pickups | activity_logs            │
│                     (ACID Compliant Transactions)                      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Project Directory Structure

```text
c:\Users\pandi\PROJECTS\waste-sorting-ml
├── api/                            # Vercel serverless entrypoint
│   └── index.py                    # Serverless Flask handler wrapper
├── backend/                        # Python Flask API & Deep Learning core
│   ├── app.py                      # REST API routes, RBAC decorators & database managers
│   ├── model.py                    # LiteRT/TensorFlow inference, Grad-CAM & thresholding
│   ├── train.py                    # Two-stage transfer learning & fine-tuning script
│   ├── prep_dataset.py             # Dataset preprocessing and validation utility
│   ├── class_indices.json          # 6-class index mapping
│   ├── waste_classifier.h5         # Custom fine-tuned Keras model (11.2 MB)
│   └── waste_classifier.tflite     # Quantized LiteRT FlatBuffer model (2.55 MB)
├── dataset_curated/                # 924 Verified Real-World Images (70/15/15 Split)
│   ├── train/                      # 646 Training images across 6 balanced classes
│   ├── val/                        # 137 Validation images
│   └── test/                       # 141 Untouched test images
├── docs/                           # Academic documentation & specifications
│   ├── diagrams/                   # System design, DFD, and architecture diagrams
│   └── project-report/             # Complete 10-chapter academic project report
│       └── PROJECT_REPORT.md       # Full dissertation specification
├── frontend/                       # Client web application
│   ├── admin.html                  # Administrative Governance & Retraining Console
│   ├── collector.html              # Campus Waste Collector Dispatch Portal
│   ├── index.html                  # Student Portal & AI Waste Scanner
│   ├── css/
│   │   └── ecosort.css             # EcoSort V2 Environmental Tech Design System
│   ├── js/
│   │   └── theme.js                # Theme switcher, notifications, token auth helpers
│   ├── bhc-logo.png                # Official Bishop Heber College crest
│   └── ecosort-logo.png            # EcoSort logo emblem
├── reports/                        # Empirical evaluation artifacts & figures
│   ├── confusion_matrix.png        # 141-sample test confusion matrix visualization
│   ├── evaluation_report.json      # Per-class precision, recall, and F1 metrics
│   ├── sample_gradcam.png          # Visual explanation heatmap demonstration
│   ├── training_curves.png         # Accuracy and cross-entropy loss convergence curves
│   └── training_history.json       # Epoch-by-epoch training telemetry
├── scratch/                        # Automated regression and integration test suites
│   ├── test_phase1_ui.py           # Phase 1 UI/UX design & theme validation suite (4 tests)
│   ├── test_phase2_ml.py           # Phase 2 ML pipeline, Grad-CAM & edge tests (12 tests)
│   └── test_phase3_e2e.py          # Phase 3 full lifecycle & RBAC integration suite (5 tests)
├── .env.example                    # Environment variable template
├── .gitignore                      # Git exclusion rules (ignores *.db, credentials, uploads)
├── API_DOCUMENTATION.md            # Complete REST API route specifications
├── DATASET_DOCUMENTATION.md        # Dataset provenance and curation analysis
├── DEPLOYMENT_REPORT.md            # Production deployment report (Vercel Serverless)
├── EXPERIMENT_RESULTS.md           # Deep learning hyperparameter tuning results
├── KNOWN_LIMITATIONS.md            # Technical constraints and future research roadmap
├── MODEL_EVALUATION_REPORT.md      # Empirical metrics, baseline comparisons & test results
├── MODEL_TRAINING_REPORT.md        # Two-stage transfer learning training methodology
├── requirements.txt                # Production Python dependencies
├── run.bat                         # Local one-click Windows execution batch script
├── SECURITY_AUDIT_REPORT.md        # Full security audit and remediation report
├── SYSTEM_INTEGRATION_REPORT.md    # Multi-tier system integration report
├── TESTING_REPORT.md               # 21/21 passing automated test suite execution report
└── vercel.json                     # Vercel dual-builder static + serverless routing config
```

---

## 4. Machine Learning Classification Pipeline

### Waste Stream Mapping & Reward Metrics

The classification engine maps incoming imagery into six categories aligned with Bishop Heber College's waste management infrastructure:

| Category | Bin Designation | Color Code | Student Reward | Carbon Offset | Campus Disposal Guidance |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Organic** | Compost Pit | Green | +5 pts | 0.4 kg CO₂ | Deposit in green compost bins. Exclude non-biodegradable wrappers or plastic stickers. |
| **Plastic** | Clean Recyclables | Blue | +10 pts | 1.2 kg CO₂ | Empty liquids, rinse, and crush bottles to reduce volume before placing in the blue bin. |
| **Paper** | Clean Recyclables | Blue | +8 pts | 0.9 kg CO₂ | Keep clean and dry. Flatten cardboard cartons and remove heavy packaging adhesive tape. |
| **Metal** | Scrap Recyclables | Red | +15 pts | 1.8 kg CO₂ | Rinse beverage cans and food tins. Deposit clean scrap in designated red bins. |
| **E-Waste** | Specialized Counter | Orange | +25 pts | 2.5 kg CO₂ | Hand over to the campus hardware repair depot or hazardous collection point. Do not crush. |
| **General** | Sanitary Landfill | Gray | +2 pts | 0.1 kg CO₂ | Non-recyclable composite waste destined for contained municipal processing. |

### Empirical Model Performance (Evaluated on $N=141$ Real Test Images)

| Evaluation Metric | Baseline Model (V1) | Improved Model (V2) | Relative Gain |
| :--- | :---: | :---: | :---: |
| **Overall Accuracy** | 36.88% | **87.94%** | **+51.06%** |
| **Macro Precision** | 31.96% | **88.50%** | **+56.54%** |
| **Macro Recall** | 36.86% | **87.75%** | **+50.89%** |
| **Macro F1-Score** | 32.20% | **87.76%** | **+55.56%** |
| **Weighted F1-Score** | 32.20% | **87.88%** | **+55.68%** |
| **Model Footprint** | 11.5 MB | **2.55 MB (LiteRT)** | **-77.8%** |

### Per-Class Test Breakdown

* **E-Waste:** Precision: **100.0%** | Recall: **100.0%** | F1-Score: **100.0%**
* **Organic:** Precision: **100.0%** | Recall: **100.0%** | F1-Score: **100.0%**
* **Paper:** Precision: **95.2%** | Recall: **83.3%** | F1-Score: **88.9%**
* **Metal:** Precision: **74.2%** | Recall: **95.8%** | F1-Score: **83.6%**
* **Plastic:** Precision: **82.6%** | Recall: **79.2%** | F1-Score: **80.9%**
* **General:** Precision: **78.9%** | Recall: **68.2%** | F1-Score: **73.2%**

---

## 5. Database Schema

The SQLite database (`waste_sorting.db`) implements ACID-compliant transactional persistence across four core tables:

```sql
-- 1. User Directory with Hierarchical RBAC
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    points INTEGER DEFAULT 0,
    co2_saved REAL DEFAULT 0.0,
    department TEXT,
    hostel TEXT,
    role TEXT DEFAULT 'Student', -- 'Student', 'Collector', 'Admin', 'SuperAdmin'
    avatar_url TEXT DEFAULT NULL,
    reg_no TEXT DEFAULT NULL,
    phone TEXT DEFAULT NULL,
    email TEXT DEFAULT NULL,
    class_name TEXT DEFAULT NULL,
    section TEXT DEFAULT NULL,
    shift TEXT DEFAULT NULL
);

-- 2. Audit Log of AI Classification Scans
CREATE TABLE IF NOT EXISTS waste_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    item_name TEXT NOT NULL,
    category TEXT NOT NULL,
    confidence REAL NOT NULL,
    points INTEGER DEFAULT 0,
    co2_offset REAL DEFAULT 0.0,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

-- 3. Bulky Campus Waste Collection Requests
CREATE TABLE IF NOT EXISTS pickups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    waste_type TEXT NOT NULL,
    block_name TEXT NOT NULL,
    room_number TEXT NOT NULL,
    date_time TEXT NOT NULL,
    status TEXT DEFAULT 'Pending', -- 'Pending', 'Claimed', 'Completed'
    claimed_by INTEGER,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (claimed_by) REFERENCES users (id)
);

-- 4. Enterprise Security Activity & Telemetry Audit Log
CREATE TABLE IF NOT EXISTS activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    details TEXT,
    ip_address TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

---

## 6. REST API Reference

All endpoints return JSON responses with standard HTTP status codes (`200 OK`, `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `500 Internal Error`). Protected routes require `Authorization: Bearer <token>`.

| Method | Endpoint | Access Level | Description |
| :--- | :--- | :---: | :--- |
| `POST` | `/api/register` | Public | Registers a student account (defaults strictly to `role: 'Student'`). |
| `POST` | `/api/login` | Public | Authenticates credentials; returns user profile and signed Bearer token. |
| `POST` | `/api/profile/update` | Authenticated | Updates student contact information and password (requires current password). |
| `POST` | `/api/profile/avatar` | Authenticated | Uploads and binds profile pictures (validates image headers). |
| `POST` | `/api/forgot-password/request` | Public | Generates a 6-digit salted OTP with 10-minute validity. |
| `POST` | `/api/forgot-password/reset` | Public | Verifies OTP against the account and resets the password securely. |
| `POST` | `/predict` | Public / Auth | Classifies waste image; returns predicted class, confidence, top-3 candidates, Grad-CAM, and guidance. |
| `GET` | `/api/logs` | Authenticated | Fetches recent scan history (IDOR protected: users only see their own scans). |
| `GET` | `/api/leaderboard` | Public | Retrieves top student environmental champions ranked by reward points. |
| `GET` | `/api/stats/departments` | Public | Aggregates recycling volumes, CO2 reductions, and points by department. |
| `GET` | `/api/pickups` | Authenticated | Retrieves pending or assigned bulk collection requests. |
| `POST` | `/api/pickups` | Student | Submits a scheduled collection request for bulky waste. |
| `POST` | `/api/pickups/claim` | Collector | Claims or marks a collection request as completed (+50 collector points). |
| `GET` | `/api/admin/stats` | Admin | Retrieves department or college-wide operational metrics and activity charts. |
| `GET` | `/api/admin/users` | Admin | Lists student directory within the administrator's authorized department. |
| `POST` | `/api/admin/users/role` | Admin | Updates user role (department admins restricted to their department). |
| `GET` | `/api/admin/activity-logs` | Admin | Audits system actions, logins, scans, and security events. |
| `GET` | `/api/admin/model-info` | Admin | Reports model version, architecture parameters, LiteRT status, and accuracy metrics. |
| `POST` | `/api/admin/retrain` | SuperAdmin | Dispatches an asynchronous model fine-tuning job in a background thread. |
| `GET` | `/api/admin/retrain/status` | SuperAdmin | Streams real-time training console logs and job completion status. |

---

## 7. Installation & Local Development

### Prerequisites
* Windows 10/11, macOS, or Linux
* Python 3.10 or Python 3.12
* Git command line tools

### Setup Steps

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/Minato0630/eco-sort.git
   cd eco-sort
   ```

2. **Configure Python Virtual Environment:**
   ```bash
   python -m venv venv
   
   # Windows PowerShell
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   source venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize Database & Run Application:**
   * **Windows One-Click:** Double-click `run.bat` or run:
     ```powershell
     .\run.bat
     ```
   * **Standard Python:**
     ```bash
     cd backend
     python app.py
     ```
   The application will initialize the SQLite schema and start serving at:
   ```text
   http://127.0.0.1:5000
   ```

---

## 8. Automated Test Suite Execution

EcoSort maintains a rigorous automated testing framework covering UI/UX elements, machine learning inference safety, and end-to-end user workflows:

```bash
# Run all three automated test suites
python scratch/test_phase1_ui.py
python scratch/test_phase2_ml.py
python scratch/test_phase3_e2e.py
```

### Verified Test Results Summary

```text
======================================================================
TEST SUITE 1: Phase 1 UI/UX Design System (scratch/test_phase1_ui.py)
----------------------------------------------------------------------
4 / 4 Tests Passed (Theme switcher, CSS integration, modal dialogs) - OK

======================================================================
TEST SUITE 2: Phase 2 Deep Learning Engine (scratch/test_phase2_ml.py)
----------------------------------------------------------------------
12 / 12 Tests Passed (LiteRT loading, [-1, 1] normalization, Grad-CAM,
                      rejection of corrupted files, uncertainty gating) - OK

======================================================================
TEST SUITE 3: Phase 3 E2E Integration (scratch/test_phase3_e2e.py)
----------------------------------------------------------------------
5 / 5 Tests Passed (Full student/collector/admin lifecycles, RBAC tokens,
                    IDOR checks, and transaction persistence) - OK

TOTAL RESULT: 21 / 21 PASS (100% Pass Rate)
======================================================================
```

---

## 9. Cloud Deployment (Vercel Serverless)

The application is deployed to production on Vercel at [https://bhc-ecosort.vercel.app/](https://bhc-ecosort.vercel.app/).

The deployment architecture utilizes a hybrid configuration specified in `vercel.json`:
* **Static Assets:** Handled by `@vercel/static` serving `frontend/**` (HTML, CSS, JS, branding assets).
* **Serverless Backend:** Python 3.12 runtime powered by `@vercel/python` executing `api/index.py`.
* **Lightweight ML Inference:** Powered by `ai-edge-litert>=1.0.1` loading the 2.55 MB LiteRT FlatBuffer model with fast cold-start performance (<1.2s).

---

## 10. Academic Project Documentation Index

For detailed dissertation chapters, design specifications, and mathematical formulations, refer to the following documentation:

| Document | Purpose & Contents |
| :--- | :--- |
| **[PROJECT_REPORT.md](file:///c:/Users/pandi/PROJECTS/waste-sorting-ml/docs/project-report/PROJECT_REPORT.md)** | Full 10-chapter academic dissertation report covering Introduction, Literature Review, System Architecture, AI Methodology, Implementation, Experimental Results, Testing, Security, and Conclusions. |
| **[MODEL_EVALUATION_REPORT.md](file:///c:/Users/pandi/PROJECTS/waste-sorting-ml/MODEL_EVALUATION_REPORT.md)** | Empirical evaluation against baseline V1: confusion matrix, precision/recall/F1, and LiteRT quantization metrics. |
| **[MODEL_TRAINING_REPORT.md](file:///c:/Users/pandi/PROJECTS/waste-sorting-ml/MODEL_TRAINING_REPORT.md)** | Two-stage transfer learning training methodology, augmentation hyper-parameters, and fine-tuning details. |
| **[SYSTEM_INTEGRATION_REPORT.md](file:///c:/Users/pandi/PROJECTS/waste-sorting-ml/SYSTEM_INTEGRATION_REPORT.md)** | Technical integration review of client, backend, database, and inference modules. |
| **[TESTING_REPORT.md](file:///c:/Users/pandi/PROJECTS/waste-sorting-ml/TESTING_REPORT.md)** | Comprehensive QA report validating 21/21 automated tests across UI, ML, and E2E suites. |
| **[SECURITY_AUDIT_REPORT.md](file:///c:/Users/pandi/PROJECTS/waste-sorting-ml/SECURITY_AUDIT_REPORT.md)** | Security vulnerability remediation report covering SEC-01 through SEC-09. |
| **[API_DOCUMENTATION.md](file:///c:/Users/pandi/PROJECTS/waste-sorting-ml/API_DOCUMENTATION.md)** | Detailed specification of all REST API endpoints, request bodies, and JSON responses. |
| **[DATASET_DOCUMENTATION.md](file:///c:/Users/pandi/PROJECTS/waste-sorting-ml/DATASET_DOCUMENTATION.md)** | Inventory and data distribution analysis for the 924 curated images. |
| **[DEPLOYMENT_REPORT.md](file:///c:/Users/pandi/PROJECTS/waste-sorting-ml/DEPLOYMENT_REPORT.md)** | Serverless edge deployment architecture and runtime configurations. |
| **[KNOWN_LIMITATIONS.md](file:///c:/Users/pandi/PROJECTS/waste-sorting-ml/KNOWN_LIMITATIONS.md)** | Identified operational constraints and future engineering roadmap. |

---

## 11. Authors & Academic Acknowledgements

* **Student Investigator:** Pandiya Gokul (`Minato0630`)  
* **Degree Programme:** Master of Science in Computer Science (M.Sc. CS)  
* **Department:** Department of Computer Science  
* **Institution:** Bishop Heber College (Autonomous), Tiruchirappalli, Tamil Nadu, India  
* **Affiliation:** Affiliated with Bharathidasan University  
* **Project Period:** 2025 – 2026 Academic Year  

*Special thanks to the faculty, research guides, and campus sanitation staff of Bishop Heber College for their valuable domain insights and support.*
