with open("frontend/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx in range(185, min(len(lines), 225)):
    print(f"{idx+1}: {lines[idx].rstrip()}")
