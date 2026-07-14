with open("frontend/index.html", "r", encoding="utf-8") as f:
    html = f.read()

lines = html.splitlines()

# Search for the closing of main content and app container before the scripts
start_idx = -1
for i, line in enumerate(lines):
    if "<!-- MOCK COMMUNICATIONS POPUP" in line:
        start_idx = i
        break

if start_idx != -1:
    print("Found communication simulation section:")
    for j in range(max(0, start_idx - 10), min(len(lines), start_idx + 35)):
        print(f"{j+1}: {lines[j]}")
