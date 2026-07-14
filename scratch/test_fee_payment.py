import requests

BASE_URL = "http://127.0.0.1:5000"

def test_payment():
    # Login green_heberite
    print("Logging in green_heberite...")
    login_res = requests.post(f"{BASE_URL}/api/login", json={"username": "green_heberite", "password": "pass123"}).json()
    user_id = login_res["user"]["id"]
    print(f"Logged in user ID: {user_id}")

    # Fetch fees
    print("Fetching outstanding fees...")
    fees = requests.get(f"{BASE_URL}/api/student/fees?user_id={user_id}").json()["fees"]
    for f in fees:
        print(f"Fee ID: {f['id']}, Type: {f['fee_type']}, Status: {f['status']}")

    # Find first pending fee
    pending_fee = next((f for f in fees if f["status"] == "Pending"), None)
    if pending_fee:
        print(f"Paying fee ID {pending_fee['id']} ({pending_fee['fee_type']})...")
        pay_res = requests.post(f"{BASE_URL}/api/student/fees/pay", json={"user_id": user_id, "fee_id": pending_fee["id"]}).json()
        print(f"Payment response: {pay_res}")

        # Fetch fees again
        updated_fees = requests.get(f"{BASE_URL}/api/student/fees?user_id={user_id}").json()["fees"]
        for f in updated_fees:
            if f["id"] == pending_fee["id"]:
                print(f"Verification - Fee ID: {f['id']}, Type: {f['fee_type']}, Status: {f['status']}, Paid Date: {f['paid_date']}")
    else:
        print("No pending fees found to pay.")

if __name__ == "__main__":
    test_payment()
