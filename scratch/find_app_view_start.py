with open("frontend/index.html", "r", encoding="utf-8") as f:
    html = f.read()

lines = html.splitlines()
for idx, line in enumerate(lines):
    if 'id="appView"' in line or 'class="app-container"' in line:
        print(f"appView starts at line {idx+1}: {line.strip()}")
        # Print 10 lines
        for j in range(idx, min(len(lines), idx + 10)):
            print(f"  {j+1}: {lines[j].strip()}")
        break
