with open("frontend/index.html", "r", encoding="utf-8") as f:
    html = f.read()

import re

# Search for overflow in CSS
print("=== OVERFLOW STYLES ===")
overflow_matches = re.findall(r'([^{}]*overflow[^{}]*\{[^}]+\})', html, re.IGNORECASE)
for match in overflow_matches:
    print(match.strip())

print("\n=== BODY AND MAIN WINDOW HEIGHT/SCROLL STYLES ===")
# Search for styles of body, html, .main-content, etc.
body_styles = re.findall(r'(body\s*\{[^}]+\})', html, re.IGNORECASE)
for match in body_styles:
    print(match.strip())

main_styles = re.findall(r'(\.main-content\s*\{[^}]+\})', html, re.IGNORECASE)
for match in main_styles:
    print(match.strip())

# Search for forgotPasswordModal or openForgotPasswordModal usage
print("\n=== FORGOT PASSWORD MODAL REFERENCES ===")
for i, line in enumerate(html.splitlines()):
    if "forgotPasswordModal" in line or "openForgotPassword" in line or "forgotPasswordLink" in line:
        print(f"Line {i+1}: {line.strip()}")
