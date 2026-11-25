# EcoSort — Complete System Integration Report

**Project Title:** EcoSort — AI-Powered Campus Waste Management System  
**Academic Document Classification:** M.Sc. Computer Science Final Year Project Technical Report  
**Phase:** Phase 3 — Complete System Integration & Production Readiness  
**Target Repository:** `Minato0630/eco-sort`  
**Git Branch:** `phase-3-system-integration`  
**Date:** November 25, 2026  

---

## 1. Executive Summary

This report provides the full technical integration review of the **EcoSort** intelligent waste sorting platform for Bishop Heber College (BHC).

In Phase 3, all disparate modules—modernized frontend interfaces, Flask REST API backend, SQLite relational persistence engine, cryptographically signed session tokens, fine-tuned MobileNetV2 LiteRT inference model, and campus pickup dispatch systems—were integrated into a unified, hardened application.

Empirical verification confirms that:
1. All three role workflows (**Student**, **Collector**, **Admin**) execute end-to-end without functional gaps or unhandled exceptions.
2. The AI waste classification pipeline operates seamlessly across client file upload, stream validation, LiteRT inference, database logging, reward point calculation, and frontend display.
3. Database integrity constraints, foreign-key relationships, and transactional commits are strictly enforced across SQLite tables.
4. Security protections (SEC-01 through SEC-09) remain active: client role escalation is prevented, sessions are cryptographically signed, and cross-user data isolation (IDOR protection) is enforced.

---

## 2. Integrated System Architecture

EcoSort uses a multi-tiered architecture structured for both local server execution and serverless edge deployment on Vercel:

```
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
│  ▼                 ▼                  ▼                 ▼              │
│ Auth & Tokens    Pickups Dispatch   Admin Analytics   Activity Audit   │
│ (ItsDangerous)   (Queue Management) (Campus Stats)   (System Logs)     │
│                                                                        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
       ┌────────────────────────────┴────────────────────────────┐
       ▼                                                         ▼
┌──────────────────────────────┐        ┌────────────────────────────────┐
│       AI INFERENCE TIER      │        │       PERSISTENCE TIER         │
│     (backend/model.py)       │        │     (waste_sorting.db)         │
│                              │        │                                │
│ • LiteRT FlatBuffer Runtime  │        │ • users (Students, Collectors) │
│ • MobileNetV2 V2 (2.55 MB)   │        │ • waste_logs (Scan History)    │
│ • [-1.0, 1.0] Preprocessing  │        │ • pickups (Dispatch Queue)     │
│ • 65% Uncertainty Cutoff     │        │ • otp_tokens (Hashed Auth)     │
│ • Grad-CAM Visual Heatmaps   │        │ • activity_logs (Audit Trail)  │
└──────────────────────────────┘        └────────────────────────────────┘
```

---

## 3. End-to-End Workflow Verification

### 3.1 Student Workflow
1. **Registration (`POST /api/register`):** Student registers with username, password, department, hostel, and contact info. Server strictly assigns the `Student` role regardless of client inputs, hashes the password via `generate_password_hash`, initializes points at 0, logs the event to `activity_logs`, and returns a signed 7-day bearer token.
2. **Login (`POST /api/login`):** Validates password hash, returns a signed JWT-equivalent token and cached user profile.
3. **Profile Management (`POST /api/profile/update`):** Enforces token verification; students cannot alter other students' accounts.
4. **AI Waste Scanner (`POST /predict`):** Image streams are verified using Pillow to reject corrupted files. MobileNetV2 LiteRT predicts category, confidence, top 3 class distribution, points (+5 to +25), and CO2 offset. If confidence is below the calibrated 65% threshold, the UI flags an uncertainty alert.
5. **Scan History (`GET /api/logs?user_id=X`):** Automatically recorded upon scan and visible in the student's personal scan activity feed.
6. **Pickup Scheduling (`POST /api/pickups`):** Student selects waste material, block (e.g., Computer Science Block, Schwartz Hostel), room/lab, and date/time. The request is created with `Pending` status.
7. **Leaderboard & Department Stats (`GET /api/leaderboard`, `GET /api/stats/departments`):** Displays student rank and cumulative campus environmental impact.

### 3.2 Collector Workflow
1. **Collector Login (`POST /api/login`):** Authenticates with `Collector` role privileges.
2. **Campus Map & Queue Inspection (`GET /api/pickups`):** Visualizes scheduled pickups on an interactive Leaflet map of Bishop Heber College campus with colored pins (Pending: Amber, Claimed: Blue, Completed: Green).
3. **Claiming Pickups (`POST /api/pickups/claim`):** Collector claims a pending order; status transitions to `Claimed` and `claimed_by` is set to the collector's ID.
4. **Collection Completion (`POST /api/pickups/claim`):** Collector completes the run; status transitions to `Completed`. The student is awarded points/CO2 in the database, the collector receives +50 volunteer points, a completed waste log is generated, and the action is recorded in `activity_logs`.

### 3.3 Administrator Workflow
1. **Admin Authentication (`POST /api/login`):** Admins (`Admin` / `SuperAdmin`) log in with server-side verified credentials. Regular department admins are scoped to their respective department.
2. **Dashboard Statistics (`GET /api/admin/stats`):** Aggregates real-time counts: total registered students, total scans, total CO2 offset, pending pickups, and waste category distributions.
3. **User Management & Promotions (`GET /api/admin/users`, `POST /api/admin/users/role`):** Enables administrators to manage students and promote qualified volunteers to the Collector role.
4. **Pickup Management (`POST /api/admin/pickups/delete`):** Allows administrative deletion or re-routing of duplicate pickup requests.
5. **Model Telemetry (`GET /api/admin/model-info`):** Returns live model metadata: version `2.0.0-mobilenetv2-finetuned`, test accuracy 87.94%, macro F1 87.76%, uncertainty cutoff 65%, and model footprint (2.55 MB LiteRT).
6. **System Activity Audit Trail (`GET /api/admin/activity-logs`):** Displays paginated audit logs of user registrations, logins, role promotions, pickups, and scanner invocations.

---

## 4. Database Integrity Verification

An automated database integrity check was executed against `waste_sorting.db`:

```text
=== DATABASE INTEGRITY AUDIT ===
Orphaned waste_logs without valid user_id: 0
Orphaned pickups without valid requester user_id: 0
Orphaned pickups with invalid claimed_by: 0
Distinct pickup statuses: ['Pending', 'Claimed', 'Completed']
Duplicate usernames: 0
User role distribution: [('Admin', 24), ('Collector', 2), ('Student', 12), ('SuperAdmin', 1)]
Users with negative points or CO2: 0
Table 'users' total rows: 39
Table 'waste_logs' total rows: 14
Table 'pickups' total rows: 4
Table 'otp_tokens' total rows: 1
Table 'activity_logs' total rows: 18
```

All foreign keys and status transitions adhere strictly to relational constraints.
