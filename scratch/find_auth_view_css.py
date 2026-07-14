with open("frontend/index.html", "r", encoding="utf-8") as f:
    html = f.read()

import re
matches = re.findall(r'(#authView\s*\{[^}]+\})', html, re.DOTALL)
print("=== #authView CSS ===")
for match in matches:
    print(match)

matches_all = re.findall(r'(\.auth-card[^{]*\{[^}]+\})', html, re.DOTALL)
print("\n=== .auth-card CSS ===")
for match in matches_all:
    print(match)
