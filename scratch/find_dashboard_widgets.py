with open("frontend/index.html", "r", encoding="utf-8") as f:
    html = f.read()

lines = html.splitlines()
start_idx = -1
for i, line in enumerate(lines):
    if 'id="dashboardTab"' in line:
        start_idx = i
        break

if start_idx != -1:
    print("Found dashboardTab:")
    for j in range(start_idx, min(len(lines), start_idx + 80)):
        print(f"{j+1}: {lines[j]}")
