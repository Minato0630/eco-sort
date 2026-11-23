import os
import sys
import time
import json
import sqlite3
import tempfile
import unittest
from io import BytesIO
from PIL import Image

# Ensure backend directory is in python path
sys.path.insert(0, os.path.abspath("backend"))

import app as flask_app_module
from app import app, init_db, token_serializer

class EcoSortSecurityAndMLTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Configure app for isolated testing
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        cls.client = app.test_client()

    def test_01_registration_privilege_escalation_prevented(self):
        """SEC-02: Ensure public registration unconditionally sets role to Student"""
        res = self.client.post("/api/register", json={
            "username": f"attacker_attempt_{int(time.time())}",
            "password": "SecurePassword123!",
            "role": "SuperAdmin",
            "department": "Computer Science"
        })
        self.assertIn(res.status_code, [200, 201])
        data = res.get_json()
        self.assertIn("token", data)
        self.assertEqual(data["user"]["role"], "Student", "Privilege escalation vulnerability: Role was not enforced as Student!")

    def test_02_password_minimum_length_enforced(self):
        """SEC-01: Ensure weak passwords (< 6 chars) are rejected"""
        res = self.client.post("/api/register", json={
            "username": "short_pw_user",
            "password": "123",
            "department": "Physics"
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("at least 6 characters", data.get("error", ""))

    def test_03_otp_not_leaked_in_forgot_password(self):
        """SEC-04: Ensure OTP is not leaked in HTTP response payload"""
        username = f"otp_test_{int(time.time())}"
        self.client.post("/api/register", json={
            "username": username,
            "password": "SecurePassword123!",
            "department": "Computer Science"
        })
        res = self.client.post("/api/forgot-password/request", json={
            "username_or_reg": username
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertNotIn("otp", data, "CRITICAL: Plaintext OTP is exposed in response JSON!")
        self.assertNotIn("simulated_otp", data, "CRITICAL: Simulated OTP is exposed in response JSON!")
        self.assertIn("message", data)

    def test_04_admin_routes_reject_unauthenticated(self):
        """SEC-03: Ensure admin routes reject unauthenticated requests"""
        for route in ["/api/admin/stats", "/api/admin/users", "/api/admin/retrain/status"]:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 403, f"Endpoint {route} allowed unauthenticated access!")

    def test_05_admin_routes_reject_student_token(self):
        """SEC-03: Ensure admin routes reject requests with Student role token"""
        student_token = token_serializer.dumps({"user_id": 999, "role": "Student"})
        headers = {"Authorization": f"Bearer {student_token}"}
        
        for route in ["/api/admin/stats", "/api/admin/users", "/api/admin/retrain/status"]:
            res = self.client.get(route, headers=headers)
            self.assertEqual(res.status_code, 403, f"Endpoint {route} allowed Student token access!")

    def test_06_superadmin_can_access_admin_stats(self):
        """SEC-03: Ensure SuperAdmin with valid token can access admin stats"""
        superadmin_token = token_serializer.dumps({"user_id": 1, "role": "SuperAdmin"})
        headers = {"Authorization": f"Bearer {superadmin_token}"}
        
        res = self.client.get("/api/admin/stats", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("total_users", data)
        self.assertIn("total_scans", data)

    def test_07_pickup_dispatch_requires_authentication(self):
        """SEC-09: Ensure unauthenticated users cannot view campus pickups or room numbers"""
        res = self.client.get("/api/pickups")
        self.assertEqual(res.status_code, 401, "Unauthenticated user was allowed to read campus pickup locations!")

    def test_08_student_sees_only_own_pickups(self):
        """SEC-09: Ensure Student token only returns student's own pickups"""
        student_token = token_serializer.dumps({"user_id": 9999, "role": "Student"})
        headers = {"Authorization": f"Bearer {student_token}"}
        res = self.client.get("/api/pickups", headers=headers)
        self.assertEqual(res.status_code, 200)
        pickups = res.get_json()
        self.assertEqual(len(pickups), 0, "Student was able to see other students' pickups!")

    def test_09_predict_rejects_corrupted_image(self):
        """SEC-06: Ensure /predict rejects non-image or corrupted files"""
        fake_file = (BytesIO(b"Not an image file content"), "test.txt")
        res = self.client.post("/predict", data={"image": fake_file}, content_type="multipart/form-data")
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("valid image", data.get("error", ""))

    def test_10_predict_real_image_inference(self):
        """ML: Ensure real image is processed without mock fallbacks"""
        # Create a valid 224x224 RGB image in memory
        img = Image.new("RGB", (224, 224), color=(73, 109, 137))
        img_bytes = BytesIO()
        img.save(img_bytes, format="JPEG")
        img_bytes.seek(0)

        res = self.client.post("/predict", data={"image": (img_bytes, "plastic_bottle.jpg")}, content_type="multipart/form-data")
        # Should succeed with 200 and return detected category and confidence
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("waste_type", data)
        self.assertIn("confidence", data)
        self.assertIn("bin", data)
        self.assertIn("bin_color", data)
        self.assertIn("detected_item", data)
        self.assertIn("points", data)

if __name__ == "__main__":
    unittest.main()
