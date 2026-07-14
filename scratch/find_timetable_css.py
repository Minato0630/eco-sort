with open("frontend/index.html", "r", encoding="utf-8") as f:
    html = f.read()

import re
matches = re.findall(r'(\.timetable-table[^{]*\{[^}]+\})', html, re.DOTALL)
print("=== TIMETABLE TABLE CSS ===")
for match in matches:
    print(match)

matches_progress = re.findall(r'(\.progress-bar[^{]*\{[^}]+\})', html, re.DOTALL)
print("\n=== PROGRESS BAR CSS ===")
for match in matches_progress:
    print(match)
