from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from model import predict_waste
import os
import sqlite3
import random
import time

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)  # Enable Cross-Origin Resource Sharing for frontend compatibility


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
    DATABASE = "waste_sorting.db"
    UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# In-memory store for OTPs: user_id -> {"otp": "...", "expires": ...}
forgot_otps = {}


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
            
        # Check if users are empty and seed mock data for BHC
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            demo_users = [
                ('green_heberite', generate_password_hash('pass123'), 450, 42.6, 'Computer Science', 'Schwartz Hostel', 'Student', '211105001', '9876543210', 'green_heberite@bhc.edu.in', 'B.Sc. Computer Science', 'A', 'Shift I'),
                ('compost_queen', generate_password_hash('pass123'), 610, 58.4, 'Biotechnology', 'All Saints Hostel', 'Student', '211105002', '9876543211', 'compost_queen@bhc.edu.in', 'B.Sc. Biotechnology', 'B', 'Shift I'),
                ('recycler_bba', generate_password_hash('pass123'), 210, 19.3, 'Management Studies', 'Day Scholar', 'Student', '211105003', '9876543212', 'recycler_bba@bhc.edu.in', 'BBA', 'A', 'Shift II'),
                ('eco_physics', generate_password_hash('pass123'), 340, 31.8, 'Physics', 'Gardiner Hostel', 'Student', '211105004', '9876543213', 'eco_physics@bhc.edu.in', 'B.Sc. Physics', 'C', 'Shift I')
            ]
            conn.executemany(
                "INSERT INTO users (username, password, points, co2_saved, department, hostel, role, reg_no, phone, email, class_name, section, shift) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                demo_users
            )
            # Add some demo activity logs
            conn.execute("INSERT INTO waste_logs (user_id, item_name, category, confidence, points, co2_offset) VALUES (1, 'Water Bottle', 'Recyclable (Plastic)', 94.5, 10, 1.2)")
            conn.execute("INSERT INTO waste_logs (user_id, item_name, category, confidence, points, co2_offset) VALUES (2, 'Banana Peel', 'Organic Waste', 98.7, 5, 0.4)")
            conn.execute("INSERT INTO waste_logs (user_id, item_name, category, confidence, points, co2_offset) VALUES (3, 'Computer Keyboard', 'E-Waste / Hazardous', 91.2, 25, 2.5)")
        

        
        # Seed Overall Admin (SuperAdmin)
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'super_admin'")
        if cursor.fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO users (username, password, points, co2_saved, department, hostel, role) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ('super_admin', generate_password_hash('superpass123'), 0, 0.0, 'Administration', 'Day Scholar', 'SuperAdmin')
            )
            
        # Seed 24 Department Admins (from BHC divisions)
        dept_admins = [
            ('admin_commerce', 'commerceadmin123', 'Commerce'),
            ('admin_economics', 'economicsadmin123', 'Economics'),
            ('admin_english', 'englishadmin123', 'English'),
            ('admin_history', 'historyadmin123', 'History'),
            ('admin_mgmt', 'mgmtadmin123', 'Management Studies'),
            ('admin_social', 'socialadmin123', 'Social Work'),
            ('admin_tamil', 'tamiladmin123', 'Tamil'),
            ('admin_actuarial', 'actuarialadmin123', 'Actuarial Science'),
            ('admin_aviation', 'aviationadmin123', 'Aviation'),
            ('admin_bioinformatics', 'bioinformaticsadmin123', 'Bioinformatics'),
            ('admin_biotech', 'biotechadmin123', 'Biotechnology'),
            ('admin_botany', 'botanyadmin123', 'Botany'),
            ('admin_chemistry', 'chemistryadmin123', 'Chemistry'),
            ('admin_ca', 'caadmin123', 'Computer Application'),
            ('admin_cs', 'csadmin123', 'Computer Science'),
            ('admin_ds', 'dsadmin123', 'Data Science'),
            ('admin_env', 'envadmin123', 'Environmental Sciences'),
            ('admin_it', 'itadmin123', 'Information Technology'),
            ('admin_lis', 'lisadmin123', 'Library & Inf. Science'),
            ('admin_math', 'mathadmin123', 'Mathematics'),
            ('admin_nd', 'ndadmin123', 'Nutrition & Dietetics'),
            ('admin_physics', 'physicsadmin123', 'Physics'),
            ('admin_viscom', 'viscomadmin123', 'Visual Communication'),
            ('admin_zoology', 'zoologyadmin123', 'Zoology')
        ]
        
        for username, password, dept in dept_admins:
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (username,))
            if cursor.fetchone()[0] == 0:
                conn.execute(
                    "INSERT INTO users (username, password, points, co2_saved, department, hostel, role) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (username, generate_password_hash(password), 0, 0.0, dept, 'Day Scholar', 'Admin')
                )
                
        # Seed a default collector for testing
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'collector_heber'")
        if cursor.fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO users (username, password, points, co2_saved, department, hostel, role) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ('collector_heber', generate_password_hash('collectpass123'), 120, 12.0, 'Environment Services', 'Day Scholar', 'Collector')
            )
        conn.commit()

# Initialize Database on app startup
init_db()

@app.route("/")
def home():
    return app.send_static_file("index.html")

# 1. AUTHENTICATION ENDPOINTS
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"error": "Username and password are required"}), 400
    
    username = data["username"].strip()
    password = data["password"]
    department = data.get("department", "General")
    hostel = data.get("hostel", "Day Scholar")
    role = data.get("role", "Student")
    
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
        return jsonify({
            "success": True, 
            "message": "User registered successfully", 
            "user": dict(user)
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
        return jsonify({
            "success": True,
            "message": "Login successful",
            "user": {
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
        })
    else:
        return jsonify({"error": "Invalid username or password"}), 401

# 1.1 PROFILE UPDATE & AVATAR ENDPOINTS
@app.route("/api/profile/update", methods=["POST"])
def profile_update():
    data = request.get_json()
    user_id = data.get("user_id")
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
    
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400
        
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

# 1.2 OTP FORGOT PASSWORD ENDPOINTS
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
    conn.close()
    
    if not user:
        return jsonify({"error": "User with specified username or registration number not found"}), 404
        
    user_id = user["id"]
    otp = str(random.randint(100000, 999999))
    forgot_otps[user_id] = {
        "otp": otp,
        "expires": time.time() + 600  # 10 minutes expiry
    }
    
    masked_phone = (user["phone"][:3] + "******" + user["phone"][-2:]) if user["phone"] else "your registered mobile number"
    masked_email = (user["email"][:2] + "******@" + user["email"].split("@")[-1]) if user["email"] else "your registered email"
    
    return jsonify({
        "success": True,
        "message": f"A mock OTP has been generated for demo testing.",
        "user_id": user_id,
        "otp": otp,
        "sms_simulation": f"[BHC-EcoSort SMS] Your password reset OTP is {otp}. Valid for 10 mins.",
        "email_simulation": f"[BHC-EcoSort Email] Dear Heberite, we received a request to reset your password. Use OTP: {otp} to reset your credentials.",
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
        
    otp_record = forgot_otps.get(user_id)
    if not otp_record:
        return jsonify({"error": "No OTP requested or session expired"}), 400
        
    if otp_record["otp"] != otp:
        return jsonify({"error": "Incorrect OTP. Please check the code and try again."}), 400
        
    if time.time() > otp_record["expires"]:
        del forgot_otps[user_id]
        return jsonify({"error": "OTP has expired. Please request a new one."}), 400
        
    # Reset password
    conn = get_db()
    cursor = conn.cursor()
    try:
        hashed = generate_password_hash(new_password)
        cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, user_id))
        conn.commit()
        # Clean OTP
        del forgot_otps[user_id]
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
    if os.environ.get("VERCEL"):
        return send_from_directory("/tmp/uploads/avatars", filename)
    else:
        return app.send_static_file(f"uploads/avatars/{filename}")

@app.route("/api/profile/avatar", methods=["POST"])
def profile_avatar():
    if "avatar" not in request.files:
        return jsonify({"error": "No avatar file provided"}), 400
        
    file = request.files["avatar"]
    user_id = request.form.get("user_id")
    
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400
        
    # Ensure directories exist
    if os.environ.get("VERCEL"):
        avatar_dir = "/tmp/uploads/avatars"
    else:
        avatar_dir = "frontend/uploads/avatars"
    os.makedirs(avatar_dir, exist_ok=True)
    
    # Check file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".png", ".jpg", ".jpeg", ".gif"]:
        return jsonify({"error": "Invalid file type. Allowed formats: PNG, JPG, JPEG, GIF"}), 400
        
    filename = f"avatar_{user_id}{ext}"
    dest_path = os.path.join(avatar_dir, filename)
    file.save(dest_path)
    
    # Save URL relative to frontend root
    avatar_url = f"uploads/avatars/{filename}"
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET avatar_url = ? WHERE id = ?", (avatar_url, user_id))
        conn.commit()
        
        # Fetch updated user
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
    user_id = request.form.get("user_id")  # Optional: logs prediction to active user
    
    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)

    # Run AI prediction
    result = predict_waste(path)
    
    # If user is logged in, log this waste in SQLite and award points
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
            result["user_points"] = updated["points"]
            result["user_co2_saved"] = updated["co2_saved"]
            conn.close()
        except Exception as e:
            print("Error logging waste to database:", e)
            
    return jsonify(result)

# 3. STATS & LEADERBOARD ENDPOINTS
@app.route("/api/logs", methods=["GET"])
def get_logs():
    user_id = request.args.get("user_id")
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
    # Calculate sum of points and CO2 saved by department
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

# 4. PICKUP SCHEDULING ENDPOINTS (College block/room format)
@app.route("/api/pickups", methods=["POST", "GET"])
def handle_pickups():
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == "POST":
        data = request.get_json()
        user_id = data.get("user_id")
        waste_type = data.get("waste_type")
        block_name = data.get("block_name")
        room_number = data.get("room_number")
        date_time = data.get("date_time")
        
        if not all([user_id, waste_type, block_name, room_number, date_time]):
            return jsonify({"error": "All fields are required"}), 400
            
        cursor.execute(
            "INSERT INTO pickups (user_id, waste_type, block_name, room_number, date_time) VALUES (?, ?, ?, ?, ?)",
            (user_id, waste_type, block_name, room_number, date_time)
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Campus pickup scheduled successfully"})
        
    else:
        # GET request
        cursor.execute(
            """SELECT p.id, p.user_id, p.waste_type, p.block_name, p.room_number, p.date_time, p.status, p.claimed_by, u.username as requester, c.username as collector
               FROM pickups p
               JOIN users u ON p.user_id = u.id
               LEFT JOIN users c ON p.claimed_by = c.id
               ORDER BY p.id DESC"""
        )
        pickups = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(pickups)

@app.route("/api/pickups/claim", methods=["POST"])
def claim_pickup():
    data = request.get_json()
    pickup_id = data.get("pickup_id")
    driver_id = data.get("driver_id")
    status = data.get("status", "Claimed")  # Can be 'Claimed' or 'Completed'
    
    if not pickup_id or not driver_id:
        return jsonify({"error": "Pickup ID and Driver ID are required"}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Check current pickup status
        cursor.execute("SELECT status, user_id, waste_type FROM pickups WHERE id = ?", (pickup_id,))
        pickup = cursor.fetchone()
        
        if not pickup:
            return jsonify({"error": "Pickup request not found"}), 404
            
        # Secure points allocation on completion
        if status == "Completed" and pickup["status"] != "Completed":
            # Determine points to award the student based on waste_type
            student_points = 15 # default
            wt = pickup["waste_type"].lower()
            if "e-waste" in wt or "lab" in wt: student_points = 25
            elif "plastic" in wt or "metal" in wt or "bottle" in wt or "can" in wt: student_points = 15
            elif "paper" in wt or "cardboard" in wt: student_points = 10
            
            # Award points and CO2 saved to student
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
        return jsonify({"success": True, "message": f"Pickup status updated to {status} successfully."})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Failed to update pickup: {str(e)}"}), 500
    finally:
        conn.close()

# 5. ADMIN MANAGEMENT & ASYNC RETRAINING ENDPOINTS
import threading
import subprocess

training_status = {
    "status": "Idle",
    "logs": []
}

def run_training_async():
    global training_status
    training_status["status"] = "Training"
    training_status["logs"] = ["Starting custom model training pipeline..."]
    
    try:
        # Run python backend/train.py using subprocess
        process = subprocess.Popen(
            ["venv/Scripts/python.exe", "backend/train.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        for line in process.stdout:
            training_status["logs"].append(line.strip())
            # Keep log list size reasonable (last 100 lines)
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
    admin_id = request.args.get("admin_id")
    conn = get_db()
    cursor = conn.cursor()
    
    admin_dept = None
    admin_role = "Student"
    
    if admin_id:
        cursor.execute("SELECT role, department FROM users WHERE id = ?", (admin_id,))
        admin = cursor.fetchone()
        if admin:
            admin_role = admin["role"]
            admin_dept = admin["department"]
            
    if admin_role == "SuperAdmin":
        # Global stats
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
        # Department specific stats
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
    admin_id = request.args.get("admin_id")
    conn = get_db()
    cursor = conn.cursor()
    
    admin_dept = None
    admin_role = "Student"
    
    if admin_id:
        cursor.execute("SELECT role, department FROM users WHERE id = ?", (admin_id,))
        admin = cursor.fetchone()
        if admin:
            admin_role = admin["role"]
            admin_dept = admin["department"]
            
    if admin_role == "SuperAdmin":
        cursor.execute("SELECT id, username, points, co2_saved, department, hostel, role, avatar_url FROM users ORDER BY id DESC")
    elif admin_role == "Admin" and admin_dept:
        cursor.execute(
            "SELECT id, username, points, co2_saved, department, hostel, role, avatar_url FROM users WHERE department = ? ORDER BY id DESC",
            (admin_dept,)
        )
    else:
        cursor.execute("SELECT id, username, points, co2_saved, department, hostel, role, avatar_url FROM users WHERE id = ?", (admin_id,))
        
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(users)

@app.route("/api/admin/users/role", methods=["POST"])
def admin_user_role():
    data = request.get_json()
    user_id = data.get("user_id")
    new_role = data.get("role")
    admin_id = data.get("admin_id")
    
    if not user_id or not new_role or not admin_id:
        return jsonify({"error": "User ID, role, and Admin ID are required"}), 400
        
    if new_role not in ["Student", "Collector", "Admin", "SuperAdmin"]:
        return jsonify({"error": "Invalid role specified"}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Fetch Admin details
    cursor.execute("SELECT role, department FROM users WHERE id = ?", (admin_id,))
    admin = cursor.fetchone()
    if not admin or admin["role"] not in ["Admin", "SuperAdmin"]:
        conn.close()
        return jsonify({"error": "Unauthorized. Administrative privileges required."}), 403
        
    # 2. Fetch target student details
    cursor.execute("SELECT username, department FROM users WHERE id = ?", (user_id,))
    target = cursor.fetchone()
    if not target:
        conn.close()
        return jsonify({"error": "Target user not found."}), 404
        
    # 3. Enforce department boundary for regular Admins
    if admin["role"] == "Admin":
        if admin["department"] != target["department"]:
            conn.close()
            return jsonify({"error": f"Unauthorized. You can only promote students of your own department ({admin['department']})."}), 403
            
    # 4. Perform update
    cursor.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "message": f"Successfully updated {target['username']}'s role to {new_role}."})

@app.route("/api/admin/retrain", methods=["POST"])
def admin_retrain():
    global training_status
    if training_status["status"] == "Training":
        return jsonify({"message": "Training is already in progress."}), 400
        
    thread = threading.Thread(target=run_training_async)
    thread.start()
    return jsonify({"success": True, "message": "Asynchronous AI training started."})

@app.route("/api/admin/retrain/status", methods=["GET"])
def admin_retrain_status():
    return jsonify(training_status)

@app.route("/api/admin/pickups/delete", methods=["POST"])
def admin_delete_pickup():
    data = request.get_json()
    pickup_id = data.get("pickup_id")
    
    if not pickup_id:
        return jsonify({"error": "Pickup ID is required"}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pickups WHERE id = ?", (pickup_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "message": "Pickup request deleted successfully"})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)


