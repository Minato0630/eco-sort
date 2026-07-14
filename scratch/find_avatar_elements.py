with open("frontend/index.html", "r", encoding="utf-8") as f:
    html = f.read()

lines = html.splitlines()
for idx, line in enumerate(lines):
    if "avatar" in line.lower() and "id=" in line:
        print(f"Line {idx+1}: {line.strip()}")
