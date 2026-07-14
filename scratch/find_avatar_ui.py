with open("frontend/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "function updateAvatarUI" in line:
        print(f"updateAvatarUI found at line {idx+1}")
        for j in range(idx, min(len(lines), idx + 35)):
            print(f"  {j+1}: {lines[j].rstrip()}")
        break
