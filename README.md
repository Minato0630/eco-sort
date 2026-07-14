---
title: BHC EcoSort
emoji: ♻️
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

# Bishop Heber College - EcoSort (Waste Sorting ML)

This repository contains the complete codebase and technical specification for **BHC EcoSort**, an AI-powered smart green portal customized for Bishop Heber College (BHC). The platform incorporates machine learning for waste classification, points-based gamification, inter-department leaderboards, simulated OTP password recovery, and administrative control panels for role promotion and asynchronous model retraining.

> [!IMPORTANT]
> A complete package containing all files has been zipped for your convenience.
> You can download or access the package directly: **[waste_sorting_codebase.zip](file:///C:/Users/pandi/PROJECTS/waste-sorting-ml/waste_sorting_codebase.zip)**.

---

## 1. Project Directory & Component Index
Below is the directory structure and component index. Click on any file path link to open the file directly:

```text
c:\Users\pandi\PROJECTS\waste-sorting-ml
├── .vscode/                     # Editor configurations
├── backend/                     # Python Flask API & Machine Learning core
│   ├── app.py                   # REST API server & database manager
│   ├── model.py                 # Neural network prediction & category mapper
│   ├── train.py                 # Transfer learning training pipeline script
│   ├── prep_dataset.py          # Dataset copy & subfolder distribution script
│   ├── class_indices.json       # JSON mapping for custom model indices
│   └── waste_classifier.h5      # Custom trained TensorFlow Keras model
├── dataset/                     # ML Training dataset organized by class subfolders
│   ├── E-Waste/
│   ├── General/
│   ├── Metal/
│   ├── Organic/
│   ├── Paper/
│   └── Plastic/
├── frontend/                    # Web client assets
│   ├── admin.html               # Administrative control panel Dashboard
│   ├── collector.html           # Campus Garbage Collector work order panel
│   ├── index.html               # Main Student/General User login & scanning dashboard
│   ├── bhc-logo.png             # Bishop Heber College emblem
│   ├── ecosort-logo.png         # EcoSort system branding logo
│   └── uploads/                 # Static uploads folder (holds profile avatars)
│       └── avatars/             # Saved profile picture files
├── IMAGES/                      # Local cache of training and testing images
├── requirements.txt             # Global python package specifications
├── run.bat                      # Windows one-click startup automation batch script
└── waste_sorting.db             # Local SQLite database file
```

### Components Link Map:
* **REST API Controller**: [backend/app.py](file:///C:/Users/pandi/PROJECTS/waste-sorting-ml/backend/app.py)
* **AI Model Loader & Predictor**: [backend/model.py](file:///C:/Users/pandi/PROJECTS/waste-sorting-ml/backend/model.py)
* **Transfer Learning Trainer**: [backend/train.py](file:///C:/Users/pandi/PROJECTS/waste-sorting-ml/backend/train.py)
* **Dataset Preprocessing**: [backend/prep_dataset.py](file:///C:/Users/pandi/PROJECTS/waste-sorting-ml/backend/prep_dataset.py)
* **Class Mapping Indices**: [backend/class_indices.json](file:///C:/Users/pandi/PROJECTS/waste-sorting-ml/backend/class_indices.json)
* **Main Student Portal**: [frontend/index.html](file:///C:/Users/pandi/PROJECTS/waste-sorting-ml/frontend/index.html)
* **Collector Run Portal**: [frontend/collector.html](file:///C:/Users/pandi/PROJECTS/waste-sorting-ml/frontend/collector.html)
* **Admin Dashboard**: [frontend/admin.html](file:///C:/Users/pandi/PROJECTS/waste-sorting-ml/frontend/admin.html)
* **Startup Script**: [run.bat](file:///C:/Users/pandi/PROJECTS/waste-sorting-ml/run.bat)
* **Python Requirements**: [requirements.txt](file:///C:/Users/pandi/PROJECTS/waste-sorting-ml/requirements.txt)
* **Credentials Directory**: [admin.txt](file:///C:/Users/pandi/PROJECTS/waste-sorting-ml/admin.txt)

---

## 2. Technical Stack & Dependencies

### Backend Technologies
* **Language**: Python 3.10.11
* **Framework**: Flask (v3.1.2) with Flask-Cors (v6.0.2) for cross-origin frontend requests.
* **Machine Learning**: TensorFlow (v2.20.0), NumPy (v2.2.6), and Pillow (v12.1.0) for image handling.
* **Database**: SQLite3 utilizing SQLite Row factory mappings.
* **Server**: Gunicorn (for production/Docker deployment).

### Frontend Technologies
* **Core**: Semantic HTML5 and JavaScript (Vanilla ES6).
* **Styling**: Modern CSS3 using CSS Custom Properties (CSS variables) for glassmorphic dark-theme layouts, a dark blue radial theme background (`#030712`), and Outfit typography.
* **Libraries**:
  * **Chart.js (v4.4.0)**: Interactive dashboard charts.
  * **Leaflet.js (v1.9.4)**: Canvas-based interactive mapping of campus blocks and pickup hubs.
  * **FontAwesome (v6.4.0)**: Icons for the classification bins and UI components.

---

## 3. Database Schema
The SQLite database `waste_sorting.db` is initialized on server startup via `init_db()` in [app.py](file:///C:/Users/pandi/PROJECTS/waste-sorting-ml/backend/app.py). It maintains three primary tables:

### A. `users` Table
Stores accounts with hierarchical role permissions and points metrics.
```sql
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    points INTEGER DEFAULT 0,
    co2_saved REAL DEFAULT 0.0,
    department TEXT,
    hostel TEXT,
    role TEXT DEFAULT 'Student', -- Hierarchical Roles: Student, Collector, Admin, SuperAdmin
    avatar_url TEXT DEFAULT NULL,
    reg_no TEXT DEFAULT NULL,
    phone TEXT DEFAULT NULL,
    email TEXT DEFAULT NULL,
    class_name TEXT DEFAULT NULL,
    section TEXT DEFAULT NULL,
    shift TEXT DEFAULT NULL
);
```

### B. `waste_logs` Table
Maintains logs of individual AI waste scans.
```sql
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
```

### C. `pickups` Table
Schedules bulky campus collection requests.
```sql
CREATE TABLE IF NOT EXISTS pickups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    waste_type TEXT NOT NULL,
    block_name TEXT NOT NULL,
    room_number TEXT NOT NULL,
    date_time TEXT NOT NULL,
    status TEXT DEFAULT 'Pending', -- States: Pending, Claimed, Completed
    claimed_by INTEGER,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (claimed_by) REFERENCES users (id)
);
```

---

## 4. REST API Endpoint Specifications

All endpoints are hosted in [app.py](file:///C:/Users/pandi/PROJECTS/waste-sorting-ml/backend/app.py):

### 1. Authentication Module
* **`POST /api/register`**: Validates parameters and inserts user with default role `'Student'`. Prevents duplicate usernames or registration numbers.
* **`POST /api/login`**: Validates credentials. Supports logging in using **Username** or **Registration Number**. Returns complete user metadata object.
* **`POST /api/profile/update`**: Modifies user fields. Requires current password verification for any password modification.
* **`POST /api/profile/avatar`**: Saves profile pictures locally to `frontend/uploads/avatars/avatar_<id>.<ext>` and binds filepath to the user database row.

### 2. OTP Password Recovery Module
* **`POST /api/forgot-password/request`**: Simulates sending a 6-digit OTP code to verified accounts. Stores OTP in-memory with a 10-minute expiry time limit.
* **`POST /api/forgot-password/reset`**: Verifies the sent OTP against the user ID. If valid, replaces the user's password hash with the new password.

### 3. Classification & Logs Module
* **`POST /predict`**: Accepts a multi-part file upload, saves the temporary image to `uploads/`, calls the neural network engine, awards user points and CO2 offsets, and adds a log to `waste_logs`.
* **`GET /api/logs`**: Returns the last 15 scans. If `user_id` query parameter is provided, returns user-specific scans; otherwise returns global college feed scans.
* **`GET /api/leaderboard`**: Returns the top 10 users ranked by points desc.
* **`GET /api/stats/departments`**: Aggregates point sums, CO2 reductions, and student participation counts grouped by college departments.

### 4. Bulk Pickups Module
* **`POST /api/pickups`**: Schedules a bulk pickup specifying the block, room, time, and type.
* **`GET /api/pickups`**: Retrieves all active scheduled pickups.
* **`POST /api/pickups/claim`**: Collector claims/completes a pickup. Upon completion, awards **+50 points** to the Collector, calculates student rewards based on waste type, and updates the status to `'Completed'`.
* **`POST /api/admin/pickups/delete`**: Administrative override to permanently remove a pickup request.

### 5. Retraining & Administrative Modules
* **`GET /api/admin/stats`**: Role-guarded stats. regular `Admin` accounts see department-specific aggregates; `SuperAdmin` accounts see college-wide globals.
* **`GET /api/admin/users`**: Lists the user directory (guarded by department bounds for regular department admins).
* **`POST /api/admin/users/role`**: Updates user roles (`Student`, `Collector`, `Admin`, `SuperAdmin`). regular department admins can only modify users within their department.
* **`POST /api/admin/retrain`**: Spawns an asynchronous Python thread executing [train.py](file:///C:/Users/pandi/PROJECTS/waste-sorting-ml/backend/train.py) in the background.
* **`GET /api/admin/retrain/status`**: Returns the retraining execution state (`Idle`, `Training`, `Completed`, `Failed`) along with the live terminal log buffer.

---

## 5. Machine Learning Classification Pipeline

The classification module in [model.py](file:///C:/Users/pandi/PROJECTS/waste-sorting-ml/backend/model.py) integrates a dual-mode prediction engine:

### A. Initialization & Model Fallback
```python
# Loads base MobileNetV2 pretrained on ImageNet
imagenet_model = tf.keras.applications.MobileNetV2(weights="imagenet", include_top=True)

def load_custom_model_if_available():
    global custom_model, class_indices
    if custom_model is None and os.path.exists("backend/waste_classifier.h5") and os.path.exists("backend/class_indices.json"):
        custom_model = tf.keras.models.load_model("backend/waste_classifier.h5")
        with open("backend/class_indices.json", "r") as f:
            class_indices = json.load(f)
```
* If a custom transfer learning model is present, the app utilizes it for predicting the 6 class categories.
* If unavailable, the server runs predictions against the 1000-class ImageNet MobileNetV2 model and maps the output class labels using keyword search patterns.

### B. Classification Mapping and Reward Values
Predicted labels are passed to `map_label_to_category()`, mapping products to color-coded bins and scores:

| Classification | Keyword Search Matches | Waste Bin Recommendation | Points | CO₂ saved |
| :--- | :--- | :--- | :---: | :---: |
| **E-Waste / Hazardous** | `phone`, `computer`, `laptop`, `battery`, `cable`, `bulb`, `led` | Orange Bin (Special Collection) | 25 | 2.5 kg |
| **Organic Waste** | `banana`, `apple`, `fruit`, `vegetable`, `food`, `leaf`, `compost` | Green Bin (Compost Pit) | 5 | 0.4 kg |
| **Recyclable (Plastic)** | `bottle`, `cup`, `plastic`, `container`, `wrapper`, `straw`, `pen` | Blue Bin (Recyclables) | 10 | 1.2 kg |
| **Recyclable (Paper/Cardboard)** | `paper`, `cardboard`, `box`, `book`, `magazine`, `receipt`, `sheet` | Blue Bin (Recyclables) | 8 | 0.9 kg |
| **Recyclable (Metal)** | `can`, `tin`, `metal`, `iron`, `brass`, `steel`, `foil`, `wire` | Red Bin (Metal Recyclables) | 15 | 1.8 kg |
| **General Waste / Landfill** | *Fallback default match* | Gray Bin (General Landfill) | 2 | 0.1 kg |

---

## 6. Asynchronous ML Training Pipeline
The script [train.py](file:///C:/Users/pandi/PROJECTS/waste-sorting-ml/backend/train.py) fine-tunes a custom classifier head. It does transfer learning using Keras:

1. **Dataset Structure**: Creates folders `dataset/` containing subfolders: `Organic`, `Plastic`, `Paper`, `Metal`, `E-Waste`, `General`.
2. **Data Augmentation**: Sets up an `ImageDataGenerator` configured with a 20% validation split:
   ```python
   train_datagen = ImageDataGenerator(
       rescale=1./255,
       rotation_range=20,
       width_shift_range=0.2,
       height_shift_range=0.2,
       shear_range=0.2,
       zoom_range=0.2,
       horizontal_flip=True,
       fill_mode='nearest',
       validation_split=0.2
   )
   ```
3. **Model Construction**:
   * Base architecture: `MobileNetV2` with weights from ImageNet, `include_top=False`, and frozen weights (`base_model.trainable = False`).
   * Custom Head:
     ```python
     x = tf.keras.layers.GlobalAveragePooling2D()(base_model.output)
     x = tf.keras.layers.Dense(128, activation='relu')(x)
     x = tf.keras.layers.Dropout(0.3)(x)
     outputs = tf.keras.layers.Dense(len(classes), activation='softmax')(x)
     ```
4. **Compilation & Training Parameters**:
   * Optimizer: Adam (`learning_rate=0.001`)
   * Loss: `categorical_crossentropy`
   * Metrics: `accuracy`
   * Hyperparameters: Epochs = 8, Batch Size = 4
5. **Artifacts Output**: Writes classification index mapping to `backend/class_indices.json` and exports weights to `backend/waste_classifier.h5`.

---

## 7. Dataset Setup Helper
The utility [prep_dataset.py](file:///C:/Users/pandi/PROJECTS/waste-sorting-ml/backend/prep_dataset.py) automatically processes initial image layouts. It maps raw image arrays into directory structures under their respective classes:

```python
ORIGINAL_MAPPING = {
    "Newspaper.jpg": "Paper",
    "Plastic carry bag.jpg": "Plastic",
    "Waterbottle.jpg": "Plastic",
    "apple_core.jpg": "Organic",
    "banana peel.jpg": "Organic",
    "circuit board.jpg": "E-Waste",
    "food tins.jpg": "Metal",
    "food wrapper.jpg": "General",
    "mobile wate.jpg": "E-Waste",
    "soda_can.jpg": "Metal",
    "soft drink.jpg": "Plastic"
}
```
It copies original assets from [IMAGES/](file:///C:/Users/pandi/PROJECTS/waste-sorting-ml/IMAGES) and distributes them into the structured `dataset/<class>` folders, laying the framework for immediate transfer learning model training.

---

## 8. Frontend Portal Implementations

The frontend uses a dark-theme UI with responsive sidebars and tabbed layouts:

### A. Core Styling Systems
* **Glassmorphism Variables**:
  ```css
  :root {
      --bg-color: #030712;
      --sidebar-bg: rgba(10, 15, 30, 0.7);
      --card-bg: rgba(17, 24, 39, 0.45);
      --border-color: rgba(229, 193, 88, 0.1);
      --primary: #e5c158; /* Bishop Heber College Gold */
      --secondary: #1e40af; /* Bishop Heber College Royal Blue */
  }
  ```
* Seamless animations: Hover scaling, card slides, fade-in transitions, and a looping vertical scanning laser beam effect on the web camera interface.

### B. Student Dashboard (`index.html`)
* **Authentication Forms**: Seamlessly toggles between Login, Register (including detailed BHC registration numbers, class, section, shift, and hostel details), and Forgot Password Modals.
* **AI Waste Scan Center**: Accesses the webcam via `navigator.mediaDevices.getUserMedia` or allows Drag-and-Drop image uploads. Intercepts files and updates points via Ajax `/predict` API request.
* **Bulk Collection Scheduler**: Form to schedule garbage collections, mapping college buildings like "Computer Science Block", "Admin Block", or "Schwartz Hostel".
* **Leaflet Hub Location Finder**: Centers on BHC Campus coordinates `[10.8156, 78.67336]` mapping custom marker pins representing campus recycling centers.
* **BHC Recycling Handbook**: Comprehensive list of recyclable materials showing recommended bins, award points, and carbon details.

### C. Collector Dashboard (`collector.html`)
* **Campus Map System**: Leaflet map pins reflecting active scheduled pickups colored by state (Yellow = Pending, Blue = Claimed, Green = Completed).
* **Claims Handling**: Clickable map popups or list buttons to issue `Claim` or `Collect` actions.
* **Gamified Scoreboard**: Tracking and updating collector scores on the sidebar dashboard.

### D. Admin Control Panel (`admin.html`)
* **User Promotion**: Renders list views of students allowing role changes to `Collector` or `Admin` (regular department admins are restricted to their department).
* **AI Control Room Console**: Retrain button triggering `/api/admin/retrain` endpoint. It polls `/api/admin/retrain/status` every 25 seconds, displaying real-time output terminal lines with color-coded classes (`success`, `info`, `error`).
* **Pickup Override**: Controls to remove/clear pickup entries.

---

## 9. How to Install and Run the Project

Follow these steps to set up the environment and run the application locally on Windows:

### Step 1: Install Python & Package Manager
Ensure you have Python 3.10 installed on your system.

### Step 2: Extract Project and Install Dependencies
Navigate to the root project folder:
```powershell
cd c:\Users\pandi\PROJECTS\waste-sorting-ml
```
Ensure the python virtual environment `venv` is configured. If not, create it and install packages:
```powershell
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Step 3: Start the Server Using One-Click Batch Script
Double-click the **`run.bat`** file in the root folder, or execute it in powershell:
```powershell
.\run.bat
```

The startup script will automatically:
1. Initialize the Flask backend server on `http://127.0.0.1:5000`.
2. Wait 3 seconds to let Flask start up.
3. Launch the portal directly in your default browser at **`http://127.0.0.1:5000`**.

### Step 4: Login and Test
Refer to [admin.txt](file:///C:/Users/pandi/PROJECTS/waste-sorting-ml/admin.txt) for credentials, including the Superior Admin (`super_admin` / `superpass123`) and CS Department Admin (`admin_cs` / `csadmin123`).
