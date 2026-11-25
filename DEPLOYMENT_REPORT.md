# EcoSort — Production Deployment & Infrastructure Report

**Project Title:** EcoSort — AI-Powered Campus Waste Management System  
**Deployment Platform:** Vercel Serverless Edge  
**Production URL:** `https://bhc-ecosort.vercel.app`  
**Backend Framework:** Flask / Python 3.12 (via `api/index.py`)  
**ML Engine:** LiteRT FlatBuffer (`ai-edge-litert>=1.0.1`)  
**Frontend Stack:** Semantic HTML5, CSS3 Variables (`css/ecosort.css`), Vanilla JavaScript (`js/theme.js`)  
**Date:** November 25, 2026  
**Git Branch:** `phase-3-system-integration`  

---

## 1. Vercel Deployment Architecture

EcoSort is structured as a dual-builder Vercel application combining static client delivery and serverless Python execution:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python",
      "config": {
        "pythonVersion": "3.12"
      }
    },
    {
      "src": "frontend/**",
      "use": "@vercel/static"
    }
  ],
  "routes": [
    { "src": "/api/(.*)", "dest": "/api/index.py" },
    { "src": "/predict", "dest": "/api/index.py" },
    { "src": "/admin", "dest": "/frontend/admin.html" },
    { "src": "/collector", "dest": "/frontend/collector.html" },
    { "src": "/$", "dest": "/frontend/index.html" },
    { "src": "/uploads/(.*)", "dest": "/frontend/uploads/$1" },
    { "src": "/(.*)", "dest": "/frontend/$1" }
  ]
}
```

### Key Infrastructure Fixes
1. **Resolution of `uv lock` Dependency Failure:**
   - Previous builds failed because Vercel 55.0.0 uses Python 3.12 with `uv`.
   - The legacy `tflite-runtime` package had no pre-built wheels for Python 3.12.
   - Migrating to `ai-edge-litert>=1.0.1` resolved this issue, allowing clean dependency builds.
2. **Resolution of `404: NOT_FOUND` Routing:**
   - When the `"builds"` array is declared, Vercel requires explicit builders for all deployed assets.
   - Adding `@vercel/static` for `frontend/**` ensured that `index.html`, `admin.html`, `collector.html`, and CSS/JS assets are packaged into the output bundle.

---

## 2. Serverless ML Model Considerations

Vercel Serverless Functions impose specific execution constraints:
- **Maximum Function Size:** 50 MB (zipped) / 250 MB (unzipped).
- **Execution Timeout:** 10 seconds (Hobby plan) / 60 seconds (Pro plan).
- **Cold-Start Latency:** Heavy Python libraries (such as full TensorFlow, ~450 MB) exceed serverless bundle limits and incur 10+ second cold-start delays.

### EcoSort's Optimization Strategy
- **LiteRT Model:** Exported as a compact **2.55 MB FlatBuffer** (`waste_classifier.tflite`).
- **Memory Footprint:** Operates within $\sim 45\text{ MB}$ of memory during inference.
- **Latency:** Cold start takes $< 200\text{ ms}$; warm inference takes $\sim 14\text{ ms}$.

---

## 3. Database Persistence Strategy in Serverless

### The Serverless SQLite Boundary
- On Vercel, the filesystem is **stateless and ephemeral**.
- In `backend/app.py`, when `VERCEL=1` is detected, the database seeds into `/tmp/waste_sorting.db` for ephemeral function invocation.
- While this enables testing and demonstrations on Vercel without external dependencies, changes made in one serverless lambda instance do not persist across new deployments or warm instance recycles.

### Production Migration Roadmap
For permanent production storage beyond the M.Sc. project defense:
1. **Managed PostgreSQL:** Transition to a free-tier cloud PostgreSQL provider (e.g., **Supabase** or **Neon Database**).
2. **Configuration:** Add `DATABASE_URL=postgresql://...` to Vercel Environment Variables.
3. **ORM / Driver:** Use SQLAlchemy or `psycopg2-binary` to manage connections.
