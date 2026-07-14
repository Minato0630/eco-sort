import requests
import random

BASE_URL = "http://127.0.0.1:5000"

def run():
    print("=== STARTING BHC COMPREHENSIVE WORKFLOW VERIFICATION ===\n")
    
    # Generate unique test user credentials
    rand_id = random.randint(10000, 99999)
    username = f"tester_{rand_id}"
    reg_no = f"21110{rand_id}"

    # 1. Register a new user with extended fields
    reg_payload = {
        "username": username,
        "password": "testpass123",
        "department": "Computer Science",
        "hostel": "Schwartz Hostel",
        "reg_no": reg_no,
        "phone": "9998887770",
        "email": f"{username}@bhc.edu.in",
        "class_name": "B.Sc. Computer Science",
        "section": "A",
        "shift": "Shift I"
    }
    
    print(f"Registering new BHC student: {username} (Reg No: {reg_no})...")
    r = requests.post(f"{BASE_URL}/api/register", json=reg_payload)
    if r.status_code != 201:
        print(f"Registration failed: {r.status_code} {r.text}")
        return
    print("Registration successful!")

    # 2. Login using registration number
    print(f"Testing login by Registration Number ({reg_no})...")
    login_payload = {"username": reg_no, "password": "testpass123"}
    r = requests.post(f"{BASE_URL}/api/login", json=login_payload)
    if r.status_code != 200:
        print(f"Login by reg_no failed: {r.status_code} {r.text}")
        return
            
    res_data = r.json()
    user = res_data["user"]
    user_id = user["id"]
    print(f"Logged in user ID: {user_id}, Name: {user['username']}")

    # Academic endpoint checks are skipped since Heber ERP, Student Portal, Online Fees, and Exam Results have been removed.

    # 6. Test OTP password reset flow
    print(f"Testing Forgot Password OTP generation for Reg No: {reg_no}...")
    req_otp_payload = {"username_or_reg": reg_no}
    r = requests.post(f"{BASE_URL}/api/forgot-password/request", json=req_otp_payload)
    if r.status_code != 200:
        print(f"OTP request failed: {r.status_code} {r.text}")
        return
    otp_data = r.json()
    otp = otp_data["otp"]
    print(f"Simulated SMS: {otp_data['sms_simulation']}")
    print(f"Simulated Email: {otp_data['email_simulation']}")
    print(f"Generated OTP: {otp}")

    print("Resetting password using OTP...")
    reset_payload = {
        "user_id": user_id,
        "otp": otp,
        "new_password": "newtestpass456"
    }
    r = requests.post(f"{BASE_URL}/api/forgot-password/reset", json=reset_payload)
    if r.status_code != 200:
        print(f"Password reset failed: {r.status_code} {r.text}")
        return
    print("Password reset successful!")

    # 7. Try login with new password
    print("Logging in with newly reset password...")
    r = requests.post(f"{BASE_URL}/api/login", json={"username": username, "password": "newtestpass456"})
    if r.status_code != 200:
        print(f"Login with new password failed: {r.status_code} {r.text}")
        return
    print("Login successful! User authenticated with new credentials.")
    
    print("\n=== ALL BHC API WORKFLOWS VERIFIED SUCCESSFULLY ===")

if __name__ == "__main__":
    run()
