# EcoSort — REST API Reference & Specification

**Project Title:** EcoSort — AI-Powered Campus Waste Management System  
**Version:** 2.0.0 (Hardened & Integrated)  
**Base URL:** `https://bhc-ecosort.vercel.app` (Production) / `http://localhost:5000` (Local)  
**Authentication Scheme:** Bearer Token (HTTP Authorization Header: `Bearer <token>`)  
**Payload Encoding:** JSON (`application/json`) / Multipart Form (`multipart/form-data`)  

---

## 1. Authentication & Account Endpoints

### 1.1 User Registration
- **Endpoint:** `POST /api/register`
- **Access:** Public
- **Request Body:**
  ```json
  {
    "username": "student_jdoe",
    "password": "Password@123",
    "department": "Computer Science",
    "hostel": "Schwartz Hostel",
    "email": "jdoe@bhc.edu.in",
    "phone": "9876543210",
    "reg_no": "211105099",
    "class_name": "B.Sc. Computer Science",
    "section": "A",
    "shift": "Shift I"
  }
  ```
- **Response (201 Created):**
  ```json
  {
    "success": true,
    "message": "User registered successfully",
    "token": "eyJhbGciOi...",
    "user": {
      "id": 40,
      "username": "student_jdoe",
      "role": "Student",
      "points": 0,
      "co2_saved": 0.0
    }
  }
  ```
- **Security Rule (SEC-02):** Client-supplied `role` attributes are ignored; accounts are strictly registered with the `Student` role.

### 1.2 User Login
- **Endpoint:** `POST /api/login`
- **Access:** Public
- **Request Body:**
  ```json
  {
    "username": "student_jdoe",
    "password": "Password@123"
  }
  ```
- **Response (200 OK):** Returns cryptographic bearer token valid for 7 days and full user profile dictionary.

### 1.3 Profile Update
- **Endpoint:** `POST /api/profile/update`
- **Access:** Authenticated (`Student`, `Collector`, `Admin`, `SuperAdmin`)
- **Headers:** `Authorization: Bearer <token>`
- **Request Body:**
  ```json
  {
    "user_id": 40,
    "phone": "9998887776",
    "hostel": "Gardiner Hostel"
  }
  ```
- **Security Rule (SEC-05):** Caller can only update their own account unless possessing `SuperAdmin` privileges.

### 1.4 Avatar Upload
- **Endpoint:** `POST /api/profile/avatar`
- **Access:** Authenticated
- **Payload:** `multipart/form-data` with `avatar` image file.

---

## 2. AI Waste Classification Endpoints

### 2.1 Predict Waste Category
- **Endpoint:** `POST /predict`
- **Access:** Public or Authenticated (if authenticated, points & CO2 are credited to user)
- **Headers:** Optional `Authorization: Bearer <token>`
- **Payload:** `multipart/form-data`
  - `image`: Image file (JPEG, PNG, WebP; max 16 MB)
  - `gradcam`: Optional string (`"true"` or `"false"`, default `"true"`)
- **Response (200 OK):**
  ```json
  {
    "detected_item": "Plastic",
    "raw_label": "Plastic",
    "waste_type": "Recyclable (Plastic)",
    "bin": "Blue Bin (Recyclables)",
    "bin_color": "blue",
    "confidence": 91.4,
    "points": 10,
    "co2_offset": 1.2,
    "disposal_guidance": "Empty and rinse liquids. Flatten bottles to save volume before depositing in the blue recycling bin.",
    "status": "confident",
    "is_uncertain": false,
    "uncertainty_message": null,
    "model_version": "2.0.0-mobilenetv2-finetuned",
    "top_predictions": [
      { "category": "Plastic", "confidence": 91.4 },
      { "category": "Metal", "confidence": 5.8 },
      { "category": "General", "confidence": 2.8 }
    ],
    "gradcam_image": "data:image/png;base64,...",
    "gradcam_explanation": "Grad-CAM highlights the image regions that contributed most to the model's classification...",
    "user_points": 460,
    "user_co2_saved": 43.8
  }
  ```
- **Error Responses:**
  - `400 Bad Request`: If file is missing, corrupted, or unsupported.
  - `413 Payload Too Large`: If file exceeds 16 MB.
  - `503 Service Unavailable`: If model weights cannot be loaded.

---

## 3. Campus Pickup Dispatch Endpoints

### 3.1 Schedule Pickup
- **Endpoint:** `POST /api/pickups`
- **Access:** Authenticated (`Student`)
- **Headers:** `Authorization: Bearer <token>`
- **Request Body:**
  ```json
  {
    "waste_type": "Recyclable (Plastic & Bottles)",
    "block_name": "Computer Science Block",
    "room_number": "Lab 3",
    "date_time": "2026-11-26 14:00"
  }
  ```
- **Response (200 OK):** `{"success": true, "message": "Campus pickup scheduled successfully"}`

### 3.2 List Pickups
- **Endpoint:** `GET /api/pickups`
- **Access:** Authenticated
- **Headers:** `Authorization: Bearer <token>`
- **Privacy Enforcement (SEC-09):**
  - If caller is `Student`: Returns only the caller's own pickups.
  - If caller is `Collector` or `Admin`: Returns all campus pickups for dispatch routing.

### 3.3 Claim / Complete Pickup
- **Endpoint:** `POST /api/pickups/claim`
- **Access:** Authenticated (`Collector`, `Admin`, `SuperAdmin`)
- **Headers:** `Authorization: Bearer <token>`
- **Request Body:**
  ```json
  {
    "pickup_id": 5,
    "status": "Claimed"
  }
  ```
  *(Pass `"status": "Completed"` upon successful collection run to award student points and collector volunteer score)*.

---

## 4. Leaderboard & Stats Endpoints

### 4.1 Leaderboard
- **Endpoint:** `GET /api/leaderboard`
- **Access:** Public
- **Response:** Array of top 10 ranked users sorted by total points.

### 4.2 Department Environmental Impact
- **Endpoint:** `GET /api/stats/departments`
- **Access:** Public
- **Response:** Aggregated points, total CO2 offset, and student counts grouped by college department.

### 4.3 User Scan History
- **Endpoint:** `GET /api/logs?user_id=X`
- **Access:** Authenticated (Students can access only their own history; Admins can access all).

---

## 5. Administrative Endpoints (Admin & SuperAdmin)

### 5.1 Dashboard Statistics
- **Endpoint:** `GET /api/admin/stats`
- **Access:** Admin-only (`Admin`, `SuperAdmin`)
- **Response:** Total users, total scans, total CO2 offset, pending pickups, completed pickups, category distribution breakdown.

### 5.2 User Management & Role Promotion
- **Endpoint:** `GET /api/admin/users` (List users)
- **Endpoint:** `POST /api/admin/users/role` (Promote / change role)
- **Access:** Admin-only

### 5.3 Model Telemetry & Status
- **Endpoint:** `GET /api/admin/model-info`
- **Access:** Admin-only
- **Response:** Model version, architecture, test accuracy, macro F1, footprint size, uncertainty threshold.

### 5.4 System Activity Audit Logs
- **Endpoint:** `GET /api/admin/activity-logs?limit=50&offset=0`
- **Access:** Admin-only
- **Response:** Paginated array of audit events (Timestamp, User ID, Username, Action, Details, IP).
