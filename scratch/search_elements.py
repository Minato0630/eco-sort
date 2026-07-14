import re

with open("frontend/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# Find all lines with id="..."
lines = html.splitlines()
print("=== ELEMENTS WITH SPECIFIC ID PATTERNS ===")
for i, line in enumerate(lines):
    line_num = i + 1
    # Search for IDs related to registration, forgot, otp, erp, fees, student, results, profile
    keywords = ["auth", "reg", "forgot", "otp", "erp", "fees", "fee", "result", "profile", "password", "modal", "receipt", "payment"]
    for kw in keywords:
        if kw in line.lower() and ('id=' in line or 'class=' in line or '<button' in line or '<input' in line or '<select' in line or 'onclick' in line or '<div' in line or '<a ' in line):
            print(f"{line_num}: {line.strip()}")
            break
