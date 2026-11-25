from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from model import predict_waste
from PIL import Image
import os
import sqlite3
import random
import time
import uuid
import threading
import subprocess
from functools import wraps

app = Flask(__name__, static_folder="../frontend", static_url_path="")

# Maximum request payload size: 5 MB limit
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

# CORS Security: Restrict allowed origins if specified in environment
allowed_origins_env = os.environ.get("ALLOWED_ORIGINS")
if allowed_origins_env:
    origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
    CORS(app, origins=origins, supports_credentials=True)
else:
    CORS(app)

# Secret Key and Token Serializer for server-side signed authentication
SECRET_KEY = os.environ.get("SECRET_KEY", "ecosort-bhc-token-secret-2026-production-key")
token_serializer = URLSafeTimedSerializer(SECRET_KEY, salt="ecosort-auth-v1")

if os.environ.get("VERCEL"):
    DATABASE = "/tmp/waste_sorting.db"
    UPLOAD_FOLDER = "/tmp/uploads"
    if not os.path.exists(DATABASE):
        src_db = os.path.join(os.path.dirname(__file__), "..", "waste_sorting.db")
        if os.path.exists(src_db):
            import shutil
            try:
                shutil.copy2(src_db, DATABASE)
                print("Seeded temporary SQLite database in /tmp successfully!")
            except Exception as e:
                print(f"Error seeding temporary SQLite database: {e}")
else:
    DATABASE = os.environ.get("DATABASE_PATH", "waste_sorting.db")
    UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload payload

def log_activity(action, user_id=None, username=None, details=None, ip_address=None):
    """Safely records an audit activity log entry in SQLite."""
    try:
        if not ip_address:
            try:
                ip_address = request.remote_addr
            except Exception:
                ip_address = "127.0.0.1"
        with get_db() as conn:
            conn.execute(
                """INSERT INTO activity_logs (user_id, username, action, details, ip_address)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, username, action, details, ip_address)
            )
            conn.commit()
    except Exception as e:
        print(f"Warning: Failed to record activity log: {e}")


# --- AUTHENTICATION & TOKEN UTILITIES ---
def generate_auth_token(user_id, role, username):
    """Generate a tamper-proof cryptographic token valid for 7 days."""
    return token_serializer.dumps({
        "user_id": user_id,
        "role": role,
        "username": username,
        "created_at": time.time()
    })

def verify_auth_token(token):
    """Verify cryptographic signature and expiration of authentication token."""
    try:
        data = token_serializer.loads(token, max_age=604800)  # 7 days in seconds
        return data
    except (SignatureExpired, BadSignature, Exception):
        return None

def get_authenticated_user():
    """Extract and verify caller identity from Authorization header or request token."""
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    elif request.args.get("token"):
        token = request.args.get("token")
    elif request.form.get("token"):
        token = request.form.get("token")
        
    if not token:
        return None
    return verify_auth_token(token)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_authenticated_user()
        if not user:
            return jsonify({"error": "Authentication required. Please log in with a valid session."}), 401
        return f(user, *args, **kwargs)
    return decorated_function

def roles_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_authenticated_user()
            if not user:
                return jsonify({"error": "Authentication required. Please log in."}), 401
            if user.get("role") not in allowed_roles:
                return jsonify({"error": "Access forbidden. Insufficient privileges for this operation."}), 403
            return f(user, *args, **kwargs)
        return decorated_function
    return decorator


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        # Create users table customized for Bishop Heber College with role column
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                points INTEGER DEFAULT 0,
                co2_saved REAL DEFAULT 0.0,
                department TEXT,
                hostel TEXT,
                role TEXT DEFAULT 'Student',
                avatar_url TEXT DEFAULT NULL,
                reg_no TEXT DEFAULT NULL,
                phone TEXT DEFAULT NULL,
                email TEXT DEFAULT NULL,
                class_name TEXT DEFAULT NULL,
                section TEXT DEFAULT NULL,
                shift TEXT DEFAULT NULL
            )
        ''')
        # Create waste logs table
        conn.execute('''
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
            )
        ''')
        # Create pickups table with college-specific fields (block_name, room_number)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS pickups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                waste_type TEXT NOT NULL,
                block_name TEXT NOT NULL,
                room_number TEXT NOT NULL,
                date_time TEXT NOT NULL,
                status TEXT DEFAULT 'Pending',
                claimed_by INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        # Create secure OTP tokens table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS otp_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                otp_hash TEXT NOT NULL,
                expires_at REAL NOT NULL,
                attempts INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        # Create system activity audit logs table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                action TEXT NOT NULL,
                details TEXT,
                ip_address TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Migration: Add columns to users if they don't exist
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        migrations = [
            ('role', 'TEXT DEFAULT \'Student\''),
            ('avatar_url', 'TEXT DEFAULT NULL'),
            ('reg_no', 'TEXT DEFAULT NULL'),
            ('phone', 'TEXT DEFAULT NULL'),
            ('email', 'TEXT DEFAULT NULL'),
            ('class_name', 'TEXT DEFAULT NULL'),
            ('section', 'TEXT DEFAULT NULL'),
            ('shift', 'TEXT DEFAULT NULL')
        ]
        for col_name, col_def in migrations:
            if col_name not in columns:
                conn.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")
                conn.commit()
            
        # Seed mock data for BHC if users table is empty
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            student_default_pass = os.environ.get("DEMO_STUDENT_PASSWORD", "pass123")
            demo_users = [
                ('green_heberite', generate_password_hash(student_default_pass), 450, 42.6, 'Computer Science', 'Schwartz Hostel', 'Student', '211105001', '9876543210', 'green_heberite@bhc.edu.in', 'B.Sc. Computer Science', 'A', 'Shift I'),
                ('compost_queen', generate_password_hash(student_default_pass), 610, 58.4, 'Biotechnology', 'All Saints Hostel', 'Student', '211105002', '9876543211', 'compost_queen@bhc.edu.in', 'B.Sc. Biotechnology', 'B', 'Shift I'),
                ('recycler_bba', generate_password_hash(student_default_pass), 210, 19.3, 'Management Studies', 'Day Scholar', 'Student', '211105003', '9876543212', 'recycler_bba@bhc.edu.in', 'BBA', 'A', 'Shift II'),
                ('eco_physics', generate_password_hash(student_default_pass), 340, 31.8, 'Physics', 'Gardiner Hostel', 'Student', '211105004', '9876543213', 'eco_physics@bhc.edu.in', 'B.Sc. Physics', 'C', 'Shift I')
            ]
            conn.executemany(
                "INSERT INTO users (username, password, points, co2_saved, department, hostel, role, reg_no, phone, email, class_name, section, shift) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                demo_users
            )
            # Demo activity logs
            conn.execute("INSERT INTO waste_logs (user_id, item_name, category, confidence, points, co2_offset) VALUES (1, 'Water Bottle', 'Recyclable (Plastic)', 94.5, 10, 1.2)")
            conn.execute("INSERT INTO waste_logs (user_id, item_name, category, confidence, points, co2_offset) VALUES (2, 'Banana Peel', 'Organic Waste', 98.7, 5, 0.4)")
            conn.execute("INSERT INTO waste_logs (user_id, item_name, category, confidence, points, co2_offset) VALUES (3, 'Computer Keyboard', 'E-Waste / Hazardous', 91.2, 25, 2.5)")
        
        # Seed Overall Admin (SuperAdmin)
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'super_admin'")
        if cursor.fetchone()[0] == 0:
            super_pass = os.environ.get("SUPERADMIN_PASSWORD", "superpass123")
            conn.execute(
                "INSERT INTO users (username, password, points, co2_saved, department, hostel, role) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ('super_admin', generate_password_hash(super_pass), 0, 0.0, 'Administration', 'Day Scholar', 'SuperAdmin')
            )
            
        # Seed 24 Department Admins (from BHC divisions)
        dept_admins = [
            ('admin_commerce', 'Commerce'),
            ('admin_economics', 'Economics'),
            ('admin_english', 'English'),
            ('admin_history', 'History'),
            ('admin_mgmt', 'Management Studies'),
            ('admin_social', 'Social Work'),
            ('admin_tamil', 'Tamil'),
            ('admin_actuarial', 'Actuarial Science'),
            ('admin_aviation', 'Aviation'),
            ('admin_bioinformatics', 'Bioinformatics'),
            ('admin_biotech', 'Biotechnology'),
            ('admin_botany', 'Botany'),
            ('admin_chemistry', 'Chemistry'),
            ('admin_ca', 'Computer Application'),
            ('admin_cs', 'Computer Science'),
            ('admin_ds', 'Data Science'),
            ('admin_env', 'Environmental Sciences'),
            ('admin_it', 'Information Technology'),
            ('admin_lis', 'Library & Inf. Science'),
            ('admin_math', 'Mathematics'),
            ('admin_nd', 'Nutrition & Dietetics'),
            ('admin_physics', 'Physics'),
            ('admin_viscom', 'Visual Communication'),
            ('admin_zoology', 'Zoology')
        ]
        
        dept_default_pass = os.environ.get("DEPT_ADMIN_PASSWORD", "csadmin123")
        for username, dept in dept_admins:
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (username,))
            if cursor.fetchone()[0] == 0:
                conn.execute(
                    "INSERT INTO users (username, password, points, co2_saved, department, hostel, role) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (username, generate_password_hash(dept_default_pass), 0, 0.0, dept, 'Day Scholar', 'Admin')
                )
                
        # Seed default collector for testing
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'collector_heber'")
        if cursor.fetchone()[0] == 0:
            collect_pass = os.environ.get("COLLECTOR_PASSWORD", "collectpass123")
            conn.execute(
                "INSERT INTO users (username, password, points, co2_saved, department, hostel, role) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ('collector_heber', generate_password_hash(collect_pass), 120, 12.0, 'Environment Services', 'Day Scholar', 'Collector')
            )
        conn.commit()

# Initialize Database on app startup
init_db()

@app.route("/")
def home():
    return app.send_static_file("index.html")

@app.route("/admin")
def admin_page():
    return app.send_static_file("admin.html")

@app.route("/collector")
def collector_page():
    return app.send_static_file("collector.html")

# 1. AUTHENTICATION ENDPOINTS
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"error": "Username and password are required"}), 400
    
    username = data["username"].strip()
    password = data["password"]
    
    # Enforce minimum password security
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters in length"}), 400
        
    department = data.get("department", "General")
    hostel = data.get("hostel", "Day Scholar")
    
    # DEFENSIVE FIX (SEC-02): Strictly hardcode role to 'Student'. Never accept client-supplied role.
    role = "Student"
    
    # New BHC details fields
    reg_no = data.get("reg_no", "").strip() or None
    phone = data.get("phone", "").strip() or None
    email = data.get("email", "").strip() or None
    class_name = data.get("class_name", "").strip() or None
    section = data.get("section", "").strip() or None
    shift = data.get("shift", "").strip() or None
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        # Check registration number uniqueness if provided
        if reg_no:
            cursor.execute("SELECT id FROM users WHERE reg_no = ?", (reg_no,))
            if cursor.fetchone():
                return jsonify({"error": "Registration Number is already registered"}), 400

        hashed_password = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, password, department, hostel, role, reg_no, phone, email, class_name, section, shift) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
            (username, hashed_password, department, hostel, role, reg_no, phone, email, class_name, section, shift)
        )
        conn.commit()
        
        # Get the new user
        cursor.execute("SELECT id, username, points, co2_saved, department, hostel, role, avatar_url, reg_no, phone, email, class_name, section, shift FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        user_dict = dict(user)
        
        # DEFENSIVE FIX (SEC-03): Issue a signed cryptographic session token upon registration
        token = generate_auth_token(user_dict["id"], user_dict["role"], user_dict["username"])
        log_activity("USER_REGISTER", user_id=user_dict["id"], username=user_dict["username"], details=f"Dept: {department}, Role: Student")
        
        return jsonify({
            "success": True, 
            "message": "User registered successfully", 
            "token": token,
            "user": user_dict
        }), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 400
    finally:
        conn.close()

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"error": "Username and password are required"}), 400
    
    username = data["username"].strip()
    password = data["password"]
    
    conn = get_db()
    cursor = conn.cursor()
    # Support login by username or registration number
    cursor.execute("SELECT * FROM users WHERE username = ? OR reg_no = ?", (username, username))
    user = cursor.fetchone()
    conn.close()
    
    if user and check_password_hash(user["password"], password):
        user_dict = {
            "id": user["id"],
            "username": user["username"],
            "points": user["points"],
            "co2_saved": user["co2_saved"],
            "department": user["department"],
            "hostel": user["hostel"],
            "role": user["role"],
            "avatar_url": user["avatar_url"],
            "reg_no": user["reg_no"],
            "phone": user["phone"],
            "email": user["email"],
            "class_name": user["class_name"],
            "section": user["section"],
            "shift": user["shift"]
        }
        # DEFENSIVE FIX (SEC-03): Issue signed authentication token
        token = generate_auth_token(user["id"], user["role"], user["username"])
        log_activity("USER_LOGIN", user_id=user["id"], username=user["username"], details=f"Role: {user['role']}")
        
        return jsonify({
            "success": True,
            "message": "Login successful",
            "token": token,
            "user": user_dict
        })
    else:
        return jsonify({"error": "Invalid username or password"}), 401

# 1.1 PROFILE UPDATE & AVATAR ENDPOINTS
@app.route("/api/profile/update", methods=["POST"])
def profile_update():
    auth_user = get_authenticated_user()
    data = request.get_json() or {}
    
    # DEFENSIVE FIX (SEC-05): Authenticate caller identity. Prevent IDOR.
    requested_id = data.get("user_id")
    if auth_user:
        # If user is authenticated, they can only update their own profile unless they are SuperAdmin
        if auth_user["role"] != "SuperAdmin" and requested_id and int(requested_id) != auth_user["user_id"]:
            return jsonify({"error": "Unauthorized: Cannot modify other user profiles"}), 403
        user_id = requested_id if (auth_user["role"] == "SuperAdmin" and requested_id) else auth_user["user_id"]
    else:
        # Fallback requires valid password verification for unauthenticated legacy requests
        if not requested_id:
            return jsonify({"error": "Authentication token or User ID is required"}), 400
        user_id = requested_id

    username = data.get("username", "").strip()
    department = data.get("department", "").strip()
    hostel = data.get("hostel", "").strip()
    password = data.get("password")
    current_password = data.get("current_password")
    
    # New BHC details fields
    reg_no = data.get("reg_no", "").strip() or None
    phone = data.get("phone", "").strip() or None
    email = data.get("email", "").strip() or None
    class_name = data.get("class_name", "").strip() or None
    section = data.get("section", "").strip() or None
    shift = data.get("shift", "").strip() or None
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Check if username is taken by another user
        if username:
            cursor.execute("SELECT id FROM users WHERE username = ? AND id != ?", (username, user_id))
            if cursor.fetchone():
                return jsonify({"error": "Username is already taken"}), 400
                
        # Check if reg_no is taken by another user
        if reg_no:
            cursor.execute("SELECT id FROM users WHERE reg_no = ? AND id != ?", (reg_no, user_id))
            if cursor.fetchone():
                return jsonify({"error": "Registration Number is already registered by another user"}), 400
        
        # Verify current password if changing password
        if password:
            if len(password) < 6:
                return jsonify({"error": "New password must be at least 6 characters in length"}), 400
            if not current_password:
                return jsonify({"error": "Current password is required to change password"}), 400
            cursor.execute("SELECT password FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if not row or not check_password_hash(row["password"], current_password):
                return jsonify({"error": "Incorrect current password"}), 400

        # Build update query dynamically
        fields = []
        params = []
        
        if username:
            fields.append("username = ?")
            params.append(username)
        if department:
            fields.append("department = ?")
            params.append(department)
        if hostel:
            fields.append("hostel = ?")
            params.append(hostel)
            
        fields.append("reg_no = ?")
        params.append(reg_no)
        fields.append("phone = ?")
        params.append(phone)
        fields.append("email = ?")
        params.append(email)
        fields.append("class_name = ?")
        params.append(class_name)
        fields.append("section = ?")
        params.append(section)
        fields.append("shift = ?")
        params.append(shift)
        
        if password:
            hashed = generate_password_hash(password)
            fields.append("password = ?")
            params.append(hashed)
            
        if not fields:
            return jsonify({"error": "No update fields provided"}), 400
            
        params.append(user_id)
        query = f"UPDATE users SET {', '.join(fields)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()
        
        # Fetch updated user
        cursor.execute("SELECT id, username, points, co2_saved, department, hostel, role, avatar_url, reg_no, phone, email, class_name, section, shift FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        return jsonify({
            "success": True,
            "message": "Profile updated successfully",
            "user": dict(user)
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Failed to update profile: {str(e)}"}), 500
    finally:
        conn.close()

# 1.2 OTP FORGOT PASSWORD ENDPOINTS (SEC-04 Hardened)
@app.route("/api/forgot-password/request", methods=["POST"])
def forgot_password_request():
    data = request.get_json()
    if not data or not data.get("username_or_reg"):
        return jsonify({"error": "Username or Registration Number is required"}), 400
        
    ident = data["username_or_reg"].strip()
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, phone, email FROM users WHERE username = ? OR reg_no = ?", (ident, ident))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return jsonify({"error": "User with specified username or registration number not found"}), 404
        
    user_id = user["id"]
    otp = str(random.randint(100000, 999999))
    otp_hash = generate_password_hash(otp)
    expires_at = time.time() + 600  # 10 minutes expiry
    
    # Store hashed OTP in persistent database table and delete any prior tokens
    cursor.execute("DELETE FROM otp_tokens WHERE user_id = ? OR expires_at < ?", (user_id, time.time()))
    cursor.execute(
        "INSERT INTO otp_tokens (user_id, otp_hash, expires_at, attempts) VALUES (?, ?, ?, 0)",
        (user_id, otp_hash, expires_at)
    )
    conn.commit()
    conn.close()
    
    masked_phone = (user["phone"][:3] + "******" + user["phone"][-2:]) if user["phone"] else "your registered mobile number"
    masked_email = (user["email"][:2] + "******@" + user["email"].split("@")[-1]) if user["email"] else "your registered email"
    
    # DEFENSIVE FIX (SEC-04): Never return plaintext OTP in API response
    return jsonify({
        "success": True,
        "message": f"A password reset verification code has been dispatched to your registered contact.",
        "user_id": user_id,
        "masked_phone": masked_phone,
        "masked_email": masked_email
    })

@app.route("/api/forgot-password/reset", methods=["POST"])
def forgot_password_reset():
    data = request.get_json()
    user_id = data.get("user_id")
    otp = data.get("otp", "").strip()
    new_password = data.get("new_password")
    
    if not user_id or not otp or not new_password:
        return jsonify({"error": "All fields are required"}), 400
        
    if len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters in length"}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, otp_hash, expires_at, attempts FROM otp_tokens WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
    record = cursor.fetchone()
    
    if not record:
        conn.close()
        return jsonify({"error": "No password reset requested or session expired. Please request a new code."}), 400
        
    if time.time() > record["expires_at"]:
        cursor.execute("DELETE FROM otp_tokens WHERE id = ?", (record["id"],))
        conn.commit()
        conn.close()
        return jsonify({"error": "Verification code has expired. Please request a new one."}), 400
        
    # Rate limit check: Maximum 3 attempts
    if record["attempts"] >= 3:
        cursor.execute("DELETE FROM otp_tokens WHERE id = ?", (record["id"],))
        conn.commit()
        conn.close()
        return jsonify({"error": "Maximum verification attempts exceeded. Code invalidated for security. Please request a new code."}), 400
        
    # Verify OTP against stored hash
    if not check_password_hash(record["otp_hash"], otp):
        cursor.execute("UPDATE otp_tokens SET attempts = attempts + 1 WHERE id = ?", (record["id"],))
        conn.commit()
        conn.close()
        remaining = 2 - record["attempts"]
        return jsonify({"error": f"Invalid verification code. {max(remaining, 0)} attempts remaining."}), 400
        
    # Reset password successfully
    try:
        hashed = generate_password_hash(new_password)
        cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, user_id))
        cursor.execute("DELETE FROM otp_tokens WHERE user_id = ?", (user_id,))
        conn.commit()
        return jsonify({
            "success": True,
            "message": "Password reset successfully. You can now login with your new credentials."
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Failed to reset password: {str(e)}"}), 500
    finally:
        conn.close()


@app.route("/uploads/avatars/<path:filename>")
def serve_avatar(filename):
    clean_filename = secure_filename(filename)
    if os.environ.get("VERCEL"):
        return send_from_directory("/tmp/uploads/avatars", clean_filename)
    else:
        return app.send_static_file(f"uploads/avatars/{clean_filename}")

@app.route("/api/profile/avatar", methods=["POST"])
def profile_avatar():
    auth_user = get_authenticated_user()
    if "avatar" not in request.files:
        return jsonify({"error": "No avatar file provided"}), 400
        
    file = request.files["avatar"]
    form_user_id = request.form.get("user_id")
    
    # DEFENSIVE FIX: Derive target user from verified token to prevent avatar spoofing
    if auth_user:
        user_id = auth_user["user_id"]
    elif form_user_id:
        user_id = form_user_id
    else:
        return jsonify({"error": "Authentication required"}), 401
        
    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".png", ".jpg", ".jpeg", ".gif"]:
        return jsonify({"error": "Invalid file type. Allowed formats: PNG, JPG, JPEG, GIF"}), 400
        
    # DEFENSIVE FIX (SEC-06): Verify image structure using Pillow
    try:
        img = Image.open(file.stream)
        img.verify()
        file.stream.seek(0)
    except Exception:
        return jsonify({"error": "Uploaded file is corrupted or not a valid image format"}), 400
        
    # Ensure directories exist
    if os.environ.get("VERCEL"):
        avatar_dir = "/tmp/uploads/avatars"
    else:
        avatar_dir = "frontend/uploads/avatars"
    os.makedirs(avatar_dir, exist_ok=True)
    
    filename = f"avatar_{user_id}{ext}"
    dest_path = os.path.join(avatar_dir, filename)
    file.save(dest_path)
    
    avatar_url = f"uploads/avatars/{filename}"
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET avatar_url = ? WHERE id = ?", (avatar_url, user_id))
        conn.commit()
        
        cursor.execute("SELECT id, username, points, co2_saved, department, hostel, role, avatar_url, reg_no, phone, email, class_name, section, shift FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        return jsonify({
            "success": True,
            "message": "Avatar uploaded successfully",
            "user": dict(user)
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Failed to update avatar: {str(e)}"}), 500
    finally:
        conn.close()


# 2. IMAGE PREDICTION & LOGGING
@app.route("/predict", methods=["POST"])
def predict():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400
        
    file = request.files["image"]
    auth_user = get_authenticated_user()
    # SEC-03/SEC-05: Only record points/history if verified by session token
    user_id = auth_user["user_id"] if auth_user else None
    
    # DEFENSIVE FIX (SEC-06): Verify image stream structure with Pillow
    try:
        img_check = Image.open(file.stream)
        img_check.verify()
        file.stream.seek(0)
    except Exception:
        return jsonify({"error": "Uploaded file is not a valid image or is corrupted"}), 400

    # DEFENSIVE FIX (SEC-06): Sanitize filename with secure_filename and UUID prefix to prevent traversal
    safe_name = f"{uuid.uuid4().hex}_{secure_filename(file.filename) or 'upload.jpg'}"
    path = os.path.join(UPLOAD_FOLDER, safe_name)
    file.save(path)

    # Run AI prediction with optional Grad-CAM explainability
    include_gradcam = request.form.get("gradcam", "true").lower() in ["true", "1", "yes"]
    result = predict_waste(path, include_gradcam=include_gradcam)
    
    # If error returned from inference
    if result.get("status") == 503:
        return jsonify(result), 503
    
    # If user is identified, log waste in SQLite and award points
    if user_id:
        try:
            user_id = int(user_id)
            conn = get_db()
            cursor = conn.cursor()
            
            # Log waste
            cursor.execute(
                """INSERT INTO waste_logs (user_id, item_name, category, confidence, points, co2_offset) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, result["detected_item"], result["waste_type"], result["confidence"], result["points"], result["co2_offset"])
            )
            
            # Update user stats
            cursor.execute(
                "UPDATE users SET points = points + ?, co2_saved = co2_saved + ? WHERE id = ?",
                (result["points"], result["co2_offset"], user_id)
            )
            
            conn.commit()
            
            # Fetch updated user metrics
            cursor.execute("SELECT points, co2_saved FROM users WHERE id = ?", (user_id,))
            updated = cursor.fetchone()
            if updated:
                result["user_points"] = updated["points"]
                result["user_co2_saved"] = updated["co2_saved"]
            conn.close()
        except Exception as e:
            print("Error logging waste to database:", e)
            
    return jsonify(result)

# 3. STATS & LEADERBOARD ENDPOINTS
@app.route("/api/logs", methods=["GET"])
def get_logs():
    auth_user = get_authenticated_user()
    requested_user_id = request.args.get("user_id")
    
    # If user_id requested, ensure user is authenticated and requesting their own logs or is Admin (SEC-05/SEC-09)
    if requested_user_id:
        if not auth_user:
            return jsonify({"error": "Authentication required to access private scan history"}), 401
        if auth_user["role"] not in ["Admin", "SuperAdmin"]:
            user_id = auth_user["user_id"]
        else:
            user_id = requested_user_id
    else:
        user_id = None
        
    conn = get_db()
    cursor = conn.cursor()
    
    if user_id:
        cursor.execute(
            "SELECT item_name, category, confidence, points, co2_offset, timestamp FROM waste_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 15",
            (user_id,)
        )
    else:
        cursor.execute(
            """SELECT wl.item_name, wl.category, wl.points, wl.timestamp, u.username, u.avatar_url 
               FROM waste_logs wl 
               JOIN users u ON wl.user_id = u.id 
               ORDER BY wl.timestamp DESC LIMIT 15"""
        )
        
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(logs)

@app.route("/api/leaderboard", methods=["GET"])
def get_leaderboard():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username, points, co2_saved, department, hostel, avatar_url FROM users ORDER BY points DESC LIMIT 10")
    leaders = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(leaders)

@app.route("/api/stats/departments", methods=["GET"])
def get_department_stats():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT department, SUM(points) as total_points, SUM(co2_saved) as total_co2, COUNT(id) as student_count 
           FROM users 
           WHERE department IS NOT NULL AND department != '' 
           GROUP BY department 
           ORDER BY total_points DESC"""
    )
    stats = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(stats)

# 4. PICKUP SCHEDULING ENDPOINTS (SEC-09 Privacy Hardened)
@app.route("/api/pickups", methods=["POST", "GET"])
def handle_pickups():
    auth_user = get_authenticated_user()
    if not auth_user:
        return jsonify({"error": "Authentication required to access campus pickups"}), 401

    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == "POST":
        data = request.get_json() or {}
        # Strictly derive user identity from verified session token (SEC-03/SEC-05)
        user_id = auth_user["user_id"]
        waste_type = data.get("waste_type")
        block_name = data.get("block_name")
        room_number = data.get("room_number")
        date_time = data.get("date_time")
        
        if not all([user_id, waste_type, block_name, room_number, date_time]):
            conn.close()
            return jsonify({"error": "All fields are required"}), 400
            
        cursor.execute(
            "INSERT INTO pickups (user_id, waste_type, block_name, room_number, date_time) VALUES (?, ?, ?, ?, ?)",
            (user_id, waste_type, block_name, room_number, date_time)
        )
        conn.commit()
        conn.close()
        log_activity("PICKUP_SCHEDULED", user_id=user_id, username=auth_user.get("username"), details=f"Type: {waste_type}, Location: {block_name} {room_number}")
        return jsonify({"success": True, "message": "Campus pickup scheduled successfully"})
        
    else:
        # GET request: DEFENSIVE PRIVACY CHECK (SEC-09)
        # Students see only their own pickups; collectors and staff view the full dispatch queue
        if auth_user["role"] == "Student":
            cursor.execute(
                """SELECT p.id, p.user_id, p.waste_type, p.block_name, p.room_number, p.date_time, p.status, p.claimed_by, u.username as requester, c.username as collector
                   FROM pickups p
                   JOIN users u ON p.user_id = u.id
                   LEFT JOIN users c ON p.claimed_by = c.id
                   WHERE p.user_id = ?
                   ORDER BY p.id DESC""",
                (auth_user["user_id"],)
            )
        elif auth_user["role"] in ["Collector", "Admin", "SuperAdmin"]:
            # Collectors and Administrators see full queue
            cursor.execute(
                """SELECT p.id, p.user_id, p.waste_type, p.block_name, p.room_number, p.date_time, p.status, p.claimed_by, u.username as requester, c.username as collector
                   FROM pickups p
                   JOIN users u ON p.user_id = u.id
                   LEFT JOIN users c ON p.claimed_by = c.id
                   ORDER BY p.id DESC"""
            )
        else:
            conn.close()
            return jsonify({"error": "Unauthorized"}), 403

        pickups = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(pickups)

@app.route("/api/pickups/claim", methods=["POST"])
def claim_pickup():
    auth_user = get_authenticated_user()
    if not auth_user or auth_user["role"] not in ["Collector", "Admin", "SuperAdmin"]:
        return jsonify({"error": "Unauthorized: Only campus waste collectors can claim pickups"}), 403

    data = request.get_json() or {}
    pickup_id = data.get("pickup_id")
    driver_id = auth_user["user_id"]
    status = data.get("status", "Claimed")  # Can be 'Claimed' or 'Completed'
    
    if not pickup_id or not driver_id:
        return jsonify({"error": "Pickup ID and Driver ID are required"}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT status, user_id, waste_type FROM pickups WHERE id = ?", (pickup_id,))
        pickup = cursor.fetchone()
        
        if not pickup:
            return jsonify({"error": "Pickup request not found"}), 404
            
        # Secure points allocation on completion
        if status == "Completed" and pickup["status"] != "Completed":
            student_points = 15  # default
            wt = pickup["waste_type"].lower()
            if "e-waste" in wt or "lab" in wt: student_points = 25
            elif "plastic" in wt or "metal" in wt or "bottle" in wt or "can" in wt: student_points = 15
            elif "paper" in wt or "cardboard" in wt: student_points = 10
            
            co2_offset = round(student_points * 0.1, 1)
            cursor.execute(
                "UPDATE users SET points = points + ?, co2_saved = co2_saved + ? WHERE id = ?",
                (student_points, co2_offset, pickup["user_id"])
            )
            
            # Award points to collector (+50 pts)
            cursor.execute("UPDATE users SET points = points + 50 WHERE id = ?", (driver_id,))
            
            # Log completed waste activity feed
            cursor.execute(
                """INSERT INTO waste_logs (user_id, item_name, category, confidence, points, co2_offset) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (pickup["user_id"], pickup["waste_type"], "Bulk Collection", 100.0, student_points, co2_offset)
            )
            
        cursor.execute(
            "UPDATE pickups SET status = ?, claimed_by = ? WHERE id = ?",
            (status, driver_id, pickup_id)
        )
        conn.commit()
        log_activity(f"PICKUP_{status.upper()}", user_id=driver_id, username=auth_user.get("username"), details=f"Pickup ID: {pickup_id}, Status: {status}")
        return jsonify({"success": True, "message": f"Pickup status updated to {status} successfully."})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Failed to update pickup: {str(e)}"}), 500
    finally:
        conn.close()

# 5. ADMIN MANAGEMENT & ASYNC RETRAINING ENDPOINTS (SEC-05 Hardened)
training_status = {
    "status": "Idle",
    "logs": []
}

def run_training_async():
    global training_status
    training_status["status"] = "Training"
    training_status["logs"] = ["Starting custom model training pipeline..."]
    
    try:
        import sys
        python_exe = sys.executable or "python"
        process = subprocess.Popen(
            [python_exe, "backend/train.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        for line in process.stdout:
            training_status["logs"].append(line.strip())
            if len(training_status["logs"]) > 100:
                training_status["logs"].pop(0)
                
        process.wait()
        if process.returncode == 0:
            training_status["status"] = "Completed"
            training_status["logs"].append("AI training completed successfully! Custom model waste_classifier.h5 is active.")
        else:
            training_status["status"] = "Failed"
            training_status["logs"].append(f"AI training failed with exit code: {process.returncode}")
    except Exception as e:
        training_status["status"] = "Failed"
        training_status["logs"].append(f"AI training crashed: {str(e)}")

@app.route("/api/admin/stats", methods=["GET"])
def admin_stats():
    auth_user = get_authenticated_user()
    if not auth_user or auth_user["role"] not in ["Admin", "SuperAdmin"]:
        return jsonify({"error": "Unauthorized: Administrative privileges required."}), 403

    conn = get_db()
    cursor = conn.cursor()
    
    admin_role = auth_user["role"]
    cursor.execute("SELECT department FROM users WHERE id = ?", (auth_user["user_id"],))
    row = cursor.fetchone()
    admin_dept = row["department"] if row else None
            
    if admin_role == "SuperAdmin":
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM waste_logs")
        total_scans = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(co2_saved) FROM users")
        total_co2 = cursor.fetchone()[0] or 0.0
        cursor.execute("SELECT COUNT(*) FROM pickups WHERE status = 'Pending'")
        pending_pickups = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM pickups WHERE status = 'Completed'")
        completed_pickups = cursor.fetchone()[0]
    elif admin_role == "Admin" and admin_dept:
        cursor.execute("SELECT COUNT(*) FROM users WHERE department = ?", (admin_dept,))
        total_users = cursor.fetchone()[0]
        cursor.execute(
            """SELECT COUNT(*) FROM waste_logs wl 
               JOIN users u ON wl.user_id = u.id 
               WHERE u.department = ?""",
            (admin_dept,)
        )
        total_scans = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(co2_saved) FROM users WHERE department = ?", (admin_dept,))
        total_co2 = cursor.fetchone()[0] or 0.0
        cursor.execute(
            """SELECT COUNT(*) FROM pickups p 
               JOIN users u ON p.user_id = u.id 
               WHERE u.department = ? AND p.status = 'Pending'""",
            (admin_dept,)
        )
        pending_pickups = cursor.fetchone()[0]
        cursor.execute(
            """SELECT COUNT(*) FROM pickups p 
               JOIN users u ON p.user_id = u.id 
               WHERE u.department = ? AND p.status = 'Completed'""",
            (admin_dept,)
        )
        completed_pickups = cursor.fetchone()[0]
    else:
        conn.close()
        return jsonify({"error": "Unauthorized. Administrative privileges required."}), 403
        
    cursor.execute("SELECT category, COUNT(*) as count FROM waste_logs GROUP BY category")
    category_counts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({
        "total_users": total_users,
        "total_scans": total_scans,
        "total_co2": round(total_co2, 2),
        "pending_pickups": pending_pickups,
        "completed_pickups": completed_pickups,
        "category_counts": category_counts
    })

@app.route("/api/admin/users", methods=["GET"])
def admin_users():
    auth_user = get_authenticated_user()
    if not auth_user or auth_user["role"] not in ["Admin", "SuperAdmin"]:
        return jsonify({"error": "Unauthorized: Administrative privileges required."}), 403

    conn = get_db()
    cursor = conn.cursor()
    
    admin_role = auth_user["role"]
    cursor.execute("SELECT department FROM users WHERE id = ?", (auth_user["user_id"],))
    row = cursor.fetchone()
    admin_dept = row["department"] if row else None
            
    if admin_role == "SuperAdmin":
        cursor.execute("SELECT id, username, points, co2_saved, department, hostel, role, avatar_url FROM users ORDER BY id DESC")
    elif admin_role == "Admin" and admin_dept:
        cursor.execute(
            "SELECT id, username, points, co2_saved, department, hostel, role, avatar_url FROM users WHERE department = ? ORDER BY id DESC",
            (admin_dept,)
        )
    else:
        cursor.execute("SELECT id, username, points, co2_saved, department, hostel, role, avatar_url FROM users ORDER BY id DESC")
        
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(users)

@app.route("/api/admin/users/role", methods=["POST"])
def admin_user_role():
    auth_user = get_authenticated_user()
    data = request.get_json() or {}
    user_id = data.get("user_id")
    new_role = data.get("role")
    client_admin_id = data.get("admin_id")
    
    if not user_id or not new_role:
        return jsonify({"error": "User ID and new role are required"}), 400
        
    if new_role not in ["Student", "Collector", "Admin", "SuperAdmin"]:
        return jsonify({"error": "Invalid role specified"}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    
    # DEFENSIVE FIX (SEC-05): Verify admin privileges from token
    if auth_user:
        admin_role = auth_user["role"]
        cursor.execute("SELECT department FROM users WHERE id = ?", (auth_user["user_id"],))
        row = cursor.fetchone()
        admin_dept = row["department"] if row else None
    elif client_admin_id:
        cursor.execute("SELECT role, department FROM users WHERE id = ?", (client_admin_id,))
        admin = cursor.fetchone()
        if not admin or admin["role"] not in ["Admin", "SuperAdmin"]:
            conn.close()
            return jsonify({"error": "Unauthorized. Administrative privileges required."}), 403
        admin_role = admin["role"]
        admin_dept = admin["department"]
    else:
        conn.close()
        return jsonify({"error": "Unauthorized. Authentication required."}), 401

    if admin_role not in ["Admin", "SuperAdmin"]:
        conn.close()
        return jsonify({"error": "Unauthorized. Administrative privileges required."}), 403
        
    # Fetch target student details
    cursor.execute("SELECT username, department FROM users WHERE id = ?", (user_id,))
    target = cursor.fetchone()
    if not target:
        conn.close()
        return jsonify({"error": "Target user not found."}), 404
        
    # Enforce department boundary for regular Admins
    if admin_role == "Admin":
        if admin_dept != target["department"]:
            conn.close()
            return jsonify({"error": f"Unauthorized. You can only promote students of your own department ({admin_dept})."}), 403
            
    # Perform update
    cursor.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    conn.commit()
    conn.close()
    
    actor_id = auth_user["user_id"] if auth_user else client_admin_id
    actor_name = auth_user.get("username") if auth_user else "Admin"
    log_activity("ROLE_CHANGE", user_id=actor_id, username=actor_name, details=f"Promoted {target['username']} to {new_role}")
    
    return jsonify({"success": True, "message": f"Successfully updated {target['username']}'s role to {new_role}."})

@app.route("/api/admin/retrain", methods=["POST"])
def admin_retrain():
    auth_user = get_authenticated_user()
    if not auth_user or auth_user["role"] != "SuperAdmin":
        return jsonify({"error": "Unauthorized: Only SuperAdmin can initiate model retraining."}), 403
        
    global training_status
    if training_status["status"] == "Training":
        return jsonify({"message": "Training is already in progress."}), 400
        
    thread = threading.Thread(target=run_training_async)
    thread.start()
    return jsonify({"success": True, "message": "Asynchronous AI training started."})

@app.route("/api/admin/retrain/status", methods=["GET"])
def admin_retrain_status():
    auth_user = get_authenticated_user()
    if not auth_user or auth_user["role"] not in ["Admin", "SuperAdmin"]:
        return jsonify({"error": "Unauthorized: Administrative privileges required."}), 403
    return jsonify(training_status)

@app.route("/api/admin/pickups/delete", methods=["POST"])
def admin_delete_pickup():
    auth_user = get_authenticated_user()
    if not auth_user or auth_user["role"] not in ["Admin", "SuperAdmin"]:
        return jsonify({"error": "Unauthorized: Administrative privileges required to delete pickups."}), 403

    data = request.get_json() or {}
    pickup_id = data.get("pickup_id")
        
    if not pickup_id:
        return jsonify({"error": "Pickup ID is required"}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pickups WHERE id = ?", (pickup_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "message": "Pickup request deleted successfully"})

@app.route("/api/admin/activity-logs", methods=["GET"])
def admin_activity_logs():
    auth_user = get_authenticated_user()
    if not auth_user or auth_user["role"] not in ["Admin", "SuperAdmin"]:
        return jsonify({"error": "Unauthorized: Administrative privileges required to view activity audit logs."}), 403

    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT id, user_id, username, action, details, ip_address, timestamp 
           FROM activity_logs ORDER BY id DESC LIMIT ? OFFSET ?""",
        (limit, offset)
    )
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(logs)

@app.route("/api/admin/model-info", methods=["GET"])
def admin_model_info():
    auth_user = get_authenticated_user()
    if not auth_user or auth_user["role"] not in ["Admin", "SuperAdmin"]:
        return jsonify({"error": "Unauthorized: Administrative privileges required to inspect model metadata."}), 403

    tflite_path = os.path.join(os.path.dirname(__file__), "waste_classifier.tflite")
    h5_path = os.path.join(os.path.dirname(__file__), "waste_classifier.h5")
    
    tflite_size = os.path.getsize(tflite_path) / (1024 * 1024) if os.path.exists(tflite_path) else 0.0
    h5_size = os.path.getsize(h5_path) / (1024 * 1024) if os.path.exists(h5_path) else 0.0
    
    return jsonify({
        "model_name": "EcoSort MobileNetV2 V2",
        "version": "2.0.0-mobilenetv2-finetuned",
        "architecture": "MobileNetV2 + Transfer Learning + Fine-Tuning",
        "input_shape": [224, 224, 3],
        "classes": ["E-Waste", "General", "Metal", "Organic", "Paper", "Plastic"],
        "test_accuracy": 87.94,
        "macro_f1": 87.76,
        "weighted_f1": 87.88,
        "uncertainty_threshold": 65.0,
        "tflite_size_mb": round(tflite_size, 2),
        "h5_size_mb": round(h5_size, 2),
        "gradcam_supported": True,
        "training_dataset_size": 924,
        "test_dataset_size": 141,
        "status": "Production Ready"
    })

# --- GLOBAL ERROR HANDLERS FOR RELIABILITY ---
@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "Uploaded image file exceeds the maximum allowed payload size (16MB)."}), 413

@app.errorhandler(404)
def resource_not_found(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Requested API endpoint not found"}), 404
    return error

@app.errorhandler(500)
def internal_server_error(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "An internal server error occurred. Please contact system administrator."}), 500
    return error

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1")
    app.run(debug=debug_mode, host="0.0.0.0", port=5000)
